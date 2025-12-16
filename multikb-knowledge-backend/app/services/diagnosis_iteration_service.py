"""Services for diagnosis iterations and memories."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.diagnosis_iteration import DiagnosisIteration
from app.models.diagnosis_memory import DiagnosisMemory
from app.services.base import BaseService


class DiagnosisIterationService(BaseService[DiagnosisIteration]):
    """管理诊断流程中的 Reasoning/Acting 迭代。"""

    def __init__(self, db: Session):
        super().__init__(db, DiagnosisIteration)

    async def _next_iteration_no(self, diagnosis_id: int) -> int:
        max_no = (
            self.db.query(func.max(DiagnosisIteration.iteration_no))
            .filter(
                DiagnosisIteration.diagnosis_id == diagnosis_id,
                DiagnosisIteration.is_deleted == False,  # noqa: E712
            )
            .scalar()
        )
        return int(max_no or 0) + 1

    async def start_iteration(
        self,
        diagnosis_id: int,
        stage: Optional[str] = None,
        reasoning_prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DiagnosisIteration:
        iteration_no = await self._next_iteration_no(diagnosis_id)
        payload: Dict[str, Any] = {
            "diagnosis_id": diagnosis_id,
            "iteration_no": iteration_no,
            "stage": stage,
            "status": "running",
            "reasoning_prompt": reasoning_prompt,
            "meta": metadata or {},
        }
        return await self.create(payload)

    async def complete_iteration(
        self,
        iteration_id: int,
        *,
        status: str = "completed",
        reasoning_summary: Optional[str] = None,
        reasoning_output: Optional[Any] = None,
        action_plan: Optional[Any] = None,
        action_result: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[DiagnosisIteration]:
        iteration = await self.get(iteration_id)
        if not iteration:
            return None
        iteration.status = status
        iteration.reasoning_summary = reasoning_summary or iteration.reasoning_summary
        iteration.reasoning_output = reasoning_output or iteration.reasoning_output
        iteration.action_plan = action_plan or iteration.action_plan
        iteration.action_result = action_result or iteration.action_result
        if metadata:
            # merge metadata
            merged = (iteration.meta or {}) | metadata
            iteration.meta = merged
        iteration.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(iteration)
        return iteration

    async def fail_iteration(
        self,
        iteration_id: int,
        error_message: str,
        *,
        action_plan: Optional[Any] = None,
        action_result: Optional[Any] = None,
    ) -> Optional[DiagnosisIteration]:
        return await self.complete_iteration(
            iteration_id,
            status="failed",
            reasoning_summary=error_message,
            action_plan=action_plan,
            action_result=action_result,
        )

    async def list_by_diagnosis(self, diagnosis_id: int) -> List[DiagnosisIteration]:
        return (
            self.db.query(self.model)
            .filter(
                self.model.diagnosis_id == diagnosis_id,
                self.model.is_deleted == False,  # noqa: E712
            )
            .order_by(self.model.iteration_no.asc(), self.model.created_at.asc())
            .all()
        )


class DiagnosisMemoryService(BaseService[DiagnosisMemory]):
    """管理诊断上下文记忆。"""

    def __init__(self, db: Session):
        super().__init__(db, DiagnosisMemory)

    async def add_memory(
        self,
        diagnosis_id: int,
        memory_type: str,
        summary: Optional[str],
        content: Optional[Any],
        *,
        iteration_id: Optional[int] = None,
        iteration_no: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DiagnosisMemory:
        payload: Dict[str, Any] = {
            "diagnosis_id": diagnosis_id,
            "iteration_id": iteration_id,
            "iteration_no": iteration_no,
            "memory_type": memory_type,
            "summary": summary,
            "content": content,
            "meta": metadata or {},
        }
        return await self.create(payload)

    async def bulk_add(
        self,
        diagnosis_id: int,
        memories: List[Dict[str, Any]],
    ) -> List[DiagnosisMemory]:
        results: List[DiagnosisMemory] = []
        for item in memories:
            results.append(
                await self.add_memory(
                    diagnosis_id,
                    item.get("memory_type"),
                    item.get("summary"),
                    item.get("content"),
                    iteration_id=item.get("iteration_id"),
                    iteration_no=item.get("iteration_no"),
                    metadata=item.get("metadata"),
                )
            )
        return results

    async def list_by_diagnosis(
        self,
        diagnosis_id: int,
        *,
        memory_type: Optional[str] = None,
    ) -> List[DiagnosisMemory]:
        query = (
            self.db.query(self.model)
            .filter(
                self.model.diagnosis_id == diagnosis_id,
                self.model.is_deleted == False,  # noqa: E712
            )
            .order_by(self.model.created_at.asc(), self.model.id.asc())
        )
        if memory_type:
            query = query.filter(self.model.memory_type == memory_type)
        return query.all()
