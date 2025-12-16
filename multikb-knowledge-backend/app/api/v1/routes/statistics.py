"""
Statistics API Routes
统计API路由
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import Optional
from sqlalchemy.orm import Session
from app.services.statistics_service import StatisticsService
from app.services.search_history_service import SearchHistoryService
from app.dependencies.database import get_db
from app.core.logging import logger

router = APIRouter()

def get_current_user_id(request: Request) -> int:
    """从请求中获取当前用户ID（由中间件设置）"""
    user = getattr(request.state, 'user', None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未认证")
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的用户信息")
    try:
        return int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的用户ID")

@router.get("/personal")
async def get_personal_statistics(
    request: Request,
    period: str = Query("all", description="统计周期：all/week/month/year"),
    db: Session = Depends(get_db)
):
    """获取个人数据统计"""
    try:
        user_id = get_current_user_id(request)
        logger.info(f"API请求: 获取个人统计数据，用户ID: {user_id}, 周期: {period}")
        
        service = StatisticsService(db)
        stats = await service.get_personal_statistics(user_id, period)
        
        return {
            "code": 0,
            "message": "ok",
            "data": stats
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取个人统计数据API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取个人统计数据失败: {str(e)}"
        )

@router.get("/trends")
async def get_trends(
    request: Request,
    metric: str = Query(..., description="指标：document_count/search_count/upload_count"),
    period: str = Query("month", description="周期：week/month/year"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    db: Session = Depends(get_db)
):
    """获取数据趋势"""
    try:
        user_id = get_current_user_id(request)
        logger.info(f"API请求: 获取趋势数据，用户ID: {user_id}, 指标: {metric}, 周期: {period}")
        
        service = StatisticsService(db)
        trends = await service.get_trends(user_id, metric, period, start_date, end_date)
        
        return {
            "code": 0,
            "message": "ok",
            "data": trends
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取趋势数据API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取趋势数据失败: {str(e)}"
        )

@router.get("/knowledge-bases/heatmap")
async def get_knowledge_base_heatmap(
    request: Request,
    db: Session = Depends(get_db)
):
    """获取知识库使用热力图"""
    try:
        user_id = get_current_user_id(request)
        logger.info(f"API请求: 获取知识库热力图，用户ID: {user_id}")
        
        service = StatisticsService(db)
        heatmap = await service.get_knowledge_base_heatmap(user_id)
        
        return {
            "code": 0,
            "message": "ok",
            "data": {"heatmap": heatmap}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取知识库热力图API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识库热力图失败: {str(e)}"
        )

@router.get("/search/hotwords")
async def get_search_hotwords(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    period: str = Query("week", description="周期：day/week/month"),
    db: Session = Depends(get_db)
):
    """获取搜索热词"""
    try:
        user_id = get_current_user_id(request)
        logger.info(f"API请求: 获取搜索热词，用户ID: {user_id}, 限制: {limit}, 周期: {period}")
        
        history_service = SearchHistoryService(db)
        hotwords = await history_service.get_hotwords(limit, period)
        
        # 转换为响应格式
        hotword_list = []
        for hw in hotwords:
            # 简化趋势判断（可以根据历史数据计算）
            trend = "stable"
            hotword_list.append({
                "keyword": hw.keyword,
                "count": hw.search_count,
                "trend": trend
            })
        
        return {
            "code": 0,
            "message": "ok",
            "data": {"hotwords": hotword_list}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取搜索热词API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取搜索热词失败: {str(e)}"
        )
