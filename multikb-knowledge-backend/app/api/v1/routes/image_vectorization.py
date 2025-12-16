"""
Image Vectorization API Routes
根据文档处理流程设计实现图片向量化API接口
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.services.image_vectorization_service import ImageVectorizationService
from app.dependencies.database import get_db
from app.core.logging import logger

router = APIRouter()

@router.post("/vectorize-image")
async def vectorize_image(
    file: UploadFile = File(...),
    model_type: str = "hybrid",
    db: Session = Depends(get_db)
):
    """图片向量化 - 根据设计文档实现"""
    try:
        logger.info(f"API请求: 图片向量化 {file.filename}, 模型类型: {model_type}")
        
        # 初始化图片向量化服务
        vectorizer = ImageVectorizationService()
        
        # 保存上传的图片到临时文件
        import tempfile
        import shutil
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_path = temp_file.name
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            # 根据模型类型生成向量
            if model_type == "clip":
                embedding = vectorizer.generate_clip_embedding(temp_path)
            elif model_type == "resnet":
                embedding = vectorizer.generate_resnet_embedding(temp_path)
            elif model_type == "vit":
                embedding = vectorizer.generate_vit_embedding(temp_path)
            elif model_type == "hybrid":
                embedding = vectorizer.generate_hybrid_embedding(temp_path)
            elif model_type == "multi":
                embeddings = vectorizer.generate_multi_model_embedding(temp_path)
                result = {
                    "filename": file.filename,
                    "model_type": model_type,
                    "embeddings": embeddings,
                    "embedding_dimensions": {k: len(v) for k, v in embeddings.items()},
                    "success": True
                }
                logger.info(f"API响应: 多模型向量化完成")
                return result
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"不支持的模型类型: {model_type}"
                )
            
            result = {
                "filename": file.filename,
                "model_type": model_type,
                "embedding": embedding,
                "embedding_dimension": len(embedding),
                "success": True
            }
            
            logger.info(f"API响应: 图片向量化完成，向量维度: {len(embedding)}")
            return result
            
        finally:
            # 清理临时文件
            import os
            try:
                os.unlink(temp_path)
            except:
                pass
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图片向量化API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"图片向量化失败: {str(e)}"
        )

@router.post("/batch-vectorize-images")
async def batch_vectorize_images(
    files: List[UploadFile] = File(...),
    model_type: str = "hybrid",
    db: Session = Depends(get_db)
):
    """批量图片向量化 - 根据设计文档实现"""
    try:
        logger.info(f"API请求: 批量图片向量化，文件数量: {len(files)}, 模型类型: {model_type}")
        
        # 初始化图片向量化服务
        vectorizer = ImageVectorizationService()
        
        results = []
        
        for i, file in enumerate(files):
            try:
                logger.debug(f"处理文件 {i+1}/{len(files)}: {file.filename}")
                
                # 保存上传的图片到临时文件
                import tempfile
                import shutil
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                    temp_path = temp_file.name
                
                with open(temp_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                try:
                    # 根据模型类型生成向量
                    if model_type == "clip":
                        embedding = vectorizer.generate_clip_embedding(temp_path)
                    elif model_type == "resnet":
                        embedding = vectorizer.generate_resnet_embedding(temp_path)
                    elif model_type == "vit":
                        embedding = vectorizer.generate_vit_embedding(temp_path)
                    elif model_type == "hybrid":
                        embedding = vectorizer.generate_hybrid_embedding(temp_path)
                    else:
                        embedding = []
                    
                    result = {
                        "filename": file.filename,
                        "success": True,
                        "embedding_dimension": len(embedding),
                        "error": None
                    }
                    
                except Exception as e:
                    logger.error(f"文件 {file.filename} 向量化失败: {e}")
                    result = {
                        "filename": file.filename,
                        "success": False,
                        "embedding_dimension": 0,
                        "error": str(e)
                    }
                
                finally:
                    # 清理临时文件
                    import os
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"处理文件 {file.filename} 失败: {e}")
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "embedding_dimension": 0,
                    "error": str(e)
                })
        
        success_count = sum(1 for r in results if r["success"])
        
        response = {
            "model_type": model_type,
            "total_files": len(files),
            "success_count": success_count,
            "failed_count": len(files) - success_count,
            "results": results
        }
        
        logger.info(f"API响应: 批量向量化完成，成功: {success_count}/{len(files)}")
        return response
        
    except Exception as e:
        logger.error(f"批量图片向量化API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量图片向量化失败: {str(e)}"
        )

@router.get("/model-info")
async def get_model_info(db: Session = Depends(get_db)):
    """获取模型信息 - 根据设计文档实现"""
    try:
        logger.info("API请求: 获取模型信息")
        
        # 初始化图片向量化服务
        vectorizer = ImageVectorizationService()
        
        model_info = vectorizer.get_model_info()
        
        logger.info("API响应: 模型信息获取完成")
        return model_info
        
    except Exception as e:
        logger.error(f"获取模型信息API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型信息失败: {str(e)}"
        )

@router.post("/extract-features")
async def extract_image_features(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """提取图片特征 - 根据设计文档实现"""
    try:
        logger.info(f"API请求: 提取图片特征 {file.filename}")
        
        # 初始化图片向量化服务
        vectorizer = ImageVectorizationService()
        
        # 保存上传的图片到临时文件
        import tempfile
        import shutil
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_path = temp_file.name
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            # 提取图片特征
            features = vectorizer.extract_image_features(temp_path)
            
            result = {
                "filename": file.filename,
                "features": features,
                "success": True
            }
            
            logger.info(f"API响应: 图片特征提取完成")
            return result
            
        finally:
            # 清理临时文件
            import os
            try:
                os.unlink(temp_path)
            except:
                pass
        
    except Exception as e:
        logger.error(f"提取图片特征API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提取图片特征失败: {str(e)}"
        )

@router.post("/calculate-similarity")
async def calculate_image_similarity(
    embedding1: List[float],
    embedding2: List[float],
    db: Session = Depends(get_db)
):
    """计算图片相似度 - 根据设计文档实现"""
    try:
        logger.info("API请求: 计算图片相似度")
        
        # 初始化图片向量化服务
        vectorizer = ImageVectorizationService()
        
        # 计算相似度
        similarity = vectorizer.calculate_image_similarity(embedding1, embedding2)
        
        result = {
            "similarity_score": similarity,
            "embedding1_dimension": len(embedding1),
            "embedding2_dimension": len(embedding2),
            "success": True
        }
        
        logger.info(f"API响应: 图片相似度计算完成，相似度: {similarity}")
        return result
        
    except Exception as e:
        logger.error(f"计算图片相似度API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"计算图片相似度失败: {str(e)}"
        )
