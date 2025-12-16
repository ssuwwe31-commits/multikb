import subprocess
import tempfile
import os
import shutil
from typing import Optional
from app.core.logging import logger
from app.config.settings import settings


def _resolve_soffice_path() -> Optional[str]:
    """优先使用配置的 LibreOffice 路径，找不到时自动尝试常见命令名称"""
    candidates = []
    seen = set()

    if getattr(settings, "SOFFICE_PATH", None):
        candidates.append(settings.SOFFICE_PATH)
        seen.add(settings.SOFFICE_PATH)

    for name in ("soffice", "libreoffice"):
        if name not in seen:
            candidates.append(name)
            seen.add(name)

    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    for directory in path_dirs:
        if not directory:
            continue
        try:
            for entry in os.listdir(directory):
                lower = entry.lower()
                if lower.startswith("libreoffice") or lower.startswith("soffice"):
                    full_path = os.path.join(directory, entry)
                    if os.path.isfile(full_path) or os.access(full_path, os.X_OK):
                        if full_path not in seen:
                            candidates.append(full_path)
                            seen.add(full_path)
        except OSError:
            continue

    for cand in candidates:
        if not cand:
            continue
        if os.path.isabs(cand):
            if os.path.exists(cand) and os.access(cand, os.X_OK):
                return cand
            continue
        resolved = shutil.which(cand)
        if resolved:
            return resolved
        candidate_path = os.path.abspath(cand)
        if os.path.exists(candidate_path) and os.access(candidate_path, os.X_OK):
            return candidate_path
    return None


SOFFICE_CMD = _resolve_soffice_path()


def convert_office_to_pdf(input_path: str) -> Optional[str]:
    """使用 LibreOffice 将 Office 文档（Word/Excel/PPT）转为 PDF。
    成功返回输出路径，失败返回 None。
    """
    try:
        if not os.path.exists(input_path):
            logger.error(f"LibreOffice 转换失败，文件不存在: {input_path}")
            return None
        global SOFFICE_CMD
        soffice_cmd = SOFFICE_CMD or _resolve_soffice_path()
        if not soffice_cmd:
            logger.error("LibreOffice 转换失败: 未找到 soffice/libreoffice 可执行文件，请在 .env 中配置 SOFFICE_PATH 或确保系统 PATH 中可用")
            return None
        SOFFICE_CMD = soffice_cmd
        out_dir = tempfile.mkdtemp(prefix="soffice_pdf_")
        ext = os.path.splitext(input_path)[1].lower()
        filter_map = {
            '.doc': 'writer_pdf_Export',
            '.docx': 'writer_pdf_Export',
            '.odt': 'writer_pdf_Export',
            '.ppt': 'impress_pdf_Export',
            '.pptx': 'impress_pdf_Export',
            '.odp': 'impress_pdf_Export',
            '.xls': 'calc_pdf_Export',
            '.xlsx': 'calc_pdf_Export',
            '.ods': 'calc_pdf_Export',
        }
        filter_opt = filter_map.get(ext)

        cmd = [
            soffice_cmd,
            "--headless",
            "--nologo",
            "--nodefault",
            "--nolockcheck",
            "--nofirststartwizard",
            "--convert-to",
            f"pdf{(':' + filter_opt) if filter_opt else ''}",
            "--outdir",
            out_dir,
            input_path,
        ]
        logger.info(f"[LibreOffice] 执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        logger.info(f"[LibreOffice] returncode={result.returncode}")
        if result.stdout:
            logger.info(f"[LibreOffice][stdout]\n{result.stdout}")
        if result.stderr:
            logger.warning(f"[LibreOffice][stderr]\n{result.stderr}")
        if result.returncode != 0:
            logger.error(f"[LibreOffice] 转换失败: rc={result.returncode}")
            return None
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(out_dir, f"{base}.pdf")
        if not os.path.exists(output_path):
            logger.error("LibreOffice 转换后未找到输出 PDF")
            return None
        logger.info(f"[LibreOffice] 转换成功: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"[LibreOffice] 转换异常: {e}")
        return None


# 向后兼容旧接口名称
def convert_docx_to_pdf(input_path: str) -> Optional[str]:
    return convert_office_to_pdf(input_path)


def convert_office_to_html(input_path: str) -> Optional[str]:
    """使用 LibreOffice 将 Office 文档转换为 HTML。"""
    try:
        if not os.path.exists(input_path):
            logger.error(f"LibreOffice HTML 转换失败，文件不存在: {input_path}")
            return None
        global SOFFICE_CMD
        soffice_cmd = SOFFICE_CMD or _resolve_soffice_path()
        if not soffice_cmd:
            logger.error("LibreOffice HTML 转换失败: 未找到 soffice/libreoffice 可执行文件，请配置 SOFFICE_PATH")
            return None
        SOFFICE_CMD = soffice_cmd
        out_dir = tempfile.mkdtemp(prefix="soffice_html_")
        ext = os.path.splitext(input_path)[1].lower()
        filter_map = {
            '.doc': ['writer_web_HTML'],
            '.docx': ['writer_web_HTML'],
            '.odt': ['writer_web_HTML'],
            '.ppt': ['impress_html_Export'],
            '.pptx': ['impress_html_Export'],
            '.odp': ['impress_html_Export'],
            '.xls': ['calc_HTML_Export', 'HTML (StarCalc)', 'XHTML Calc'],
            '.xlsx': ['calc_HTML_Export', 'HTML (StarCalc)', 'XHTML Calc'],
            '.ods': ['calc_HTML_Export', 'HTML (StarCalc)', 'XHTML Calc'],
        }
        filter_candidates = filter_map.get(ext, [None])
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_candidates = [
            os.path.join(out_dir, f"{base}.html"),
            os.path.join(out_dir, f"{base}.htm"),
        ]

        for filter_opt in filter_candidates:
            convert_target = f"html{(':' + filter_opt) if filter_opt else ''}"
            cmd = [
                soffice_cmd,
                "--headless",
                "--nologo",
                "--nodefault",
                "--nolockcheck",
                "--nofirststartwizard",
                "--convert-to",
                convert_target,
                "--outdir",
                out_dir,
                input_path,
            ]
            logger.info(f"[LibreOffice][HTML] 执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            logger.info(f"[LibreOffice][HTML] returncode={result.returncode}")
            if result.stdout:
                logger.info(f"[LibreOffice][HTML][stdout]\n{result.stdout}")
            if result.stderr:
                logger.warning(f"[LibreOffice][HTML][stderr]\n{result.stderr}")
            if result.returncode != 0:
                logger.error(f"[LibreOffice][HTML] 转换失败: rc={result.returncode}")
                continue
            for cand in output_candidates:
                if os.path.exists(cand):
                    logger.info(f"[LibreOffice][HTML] 转换成功: {cand}")
                    return cand
            logger.warning("[LibreOffice][HTML] 本次过滤器未生成 HTML，尝试下一种过滤器")

        logger.error("[LibreOffice][HTML] 所有过滤器均失败，未能生成 HTML")
        return None
    except Exception as e:
        logger.error(f"[LibreOffice][HTML] 转换异常: {e}")
        return None


def compress_pdf(input_pdf: str, output_pdf: str, quality: str = "screen") -> bool:
    """使用 Ghostscript 压缩 PDF。quality 可选: screen, ebook, printer, prepress.
    返回 True 表示成功，False 表示失败或未安装 gs。
    """
    try:
        gs = getattr(settings, 'GS_PATH', 'gs')
        cmd = [
            gs,
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            f'-dPDFSETTINGS=/{quality}',
            '-dNOPAUSE',
            '-dBATCH',
            '-dQUIET',
            f'-sOutputFile={output_pdf}',
            input_pdf,
        ]
        logger.info(f"[Ghostscript] 压缩PDF: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.warning(f"[Ghostscript] 压缩失败 rc={result.returncode} stderr={result.stderr[:200] if result.stderr else ''}")
            return False
        return True
    except FileNotFoundError:
        logger.warning("[Ghostscript] 未安装或GS_PATH无效，跳过PDF压缩")
        return False
    except Exception as e:
        logger.warning(f"[Ghostscript] 压缩异常: {e}")
        return False
