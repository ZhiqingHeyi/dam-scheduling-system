from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil
import subprocess
import platform
import pandas as pd
from datetime import datetime
from config import settings
import zipfile
import io

router = APIRouter()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        df = pd.read_excel(file_path)
        
        return {
            "success": True,
            "message": f"文件 {file.filename} 上传成功",
            "filename": file.filename,
            "rows": len(df),
            "columns": list(df.columns),
            "preview": df.head(5).to_dict('records')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@router.post("/upload-multiple")
async def upload_multiple_files(files: List[UploadFile] = File(...)):
    results = []
    
    for file in files:
        try:
            file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            results.append({
                "filename": file.filename,
                "success": True,
                "message": "上传成功"
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "message": str(e)
            })
    
    return {
        "success": True,
        "results": results,
        "total": len(files),
        "uploaded": sum(1 for r in results if r['success'])
    }

@router.get("/list-uploaded")
async def list_uploaded_files():
    files = []
    
    if os.path.exists(settings.UPLOAD_DIR):
        for filename in os.listdir(settings.UPLOAD_DIR):
            filepath = os.path.join(settings.UPLOAD_DIR, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append({
                    "name": filename,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "type": filename.split('.')[-1].upper()
                })
    
    return {"files": sorted(files, key=lambda x: x['modified'], reverse=True)}

@router.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(settings.OUTPUT_DIR, filename)
    
    if not os.path.exists(file_path):
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

@router.delete("/delete/{filename}")
async def delete_file(filename: str):
    file_path_upload = os.path.join(settings.UPLOAD_DIR, filename)
    file_path_output = os.path.join(settings.OUTPUT_DIR, filename)
    
    deleted = False
    
    if os.path.exists(file_path_upload):
        os.remove(file_path_upload)
        deleted = True
    
    if os.path.exists(file_path_output):
        os.remove(file_path_output)
        deleted = True
    
    if deleted:
        return {"success": True, "message": f"文件 {filename} 已删除"}
    else:
        raise HTTPException(status_code=404, detail="文件不存在")

@router.get("/output-files")
async def get_output_files():
    files = []
    
    run_folders = []
    if os.path.exists(settings.OUTPUT_DIR):
        for item in os.listdir(settings.OUTPUT_DIR):
            item_path = os.path.join(settings.OUTPUT_DIR, item)
            if os.path.isdir(item_path) and item.startswith("Run_"):
                run_folders.append({
                    "name": item,
                    "path": item_path,
                    "modified": datetime.fromtimestamp(os.path.getmtime(item_path)).strftime("%Y-%m-%d %H:%M:%S")
                })
    
    run_folders.sort(key=lambda x: x['modified'], reverse=True)
    
    for folder in run_folders[:5]:
        folder_files = []
        if os.path.exists(folder['path']):
            for filename in os.listdir(folder['path']):
                if filename.endswith(('.xlsx', '.png', '.csv')):
                    folder_files.append({
                        "name": filename,
                        "type": filename.split('.')[-1].upper()
                    })
        
        files.append({
            "runFolder": folder['name'],
            "timestamp": folder['modified'],
            "files": sorted(folder_files, key=lambda x: x['name'])
        })
    
    return {"runs": files}

@router.get("/preview/{filename}")
async def preview_file(filename: str):
    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    if not os.path.exists(file_path):
        file_path = os.path.join(settings.OUTPUT_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        df = pd.read_excel(file_path)

        return {
            "filename": filename,
            "rows": len(df),
            "columns": list(df.columns),
            "head": df.head(10).to_dict('records'),
            "tail": df.tail(5).to_dict('records')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"无法预览文件: {str(e)}")


@router.get("/download/{run_folder}/{filename}")
async def download_run_file(run_folder: str, filename: str):
    file_path = os.path.join(settings.OUTPUT_DIR, run_folder, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    safe_filename = os.path.basename(filename)
    return FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type='application/octet-stream'
    )


@router.get("/preview/{run_folder}/{filename}")
async def preview_run_file(run_folder: str, filename: str):
    file_path = os.path.join(settings.OUTPUT_DIR, run_folder, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        df = pd.read_excel(file_path)

        return {
            "filename": filename,
            "run_folder": run_folder,
            "rows": len(df),
            "columns": list(df.columns),
            "head": df.to_dict('records'),
            "tail": df.tail(5).to_dict('records')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"无法预览文件: {str(e)}")


@router.get("/download-run/{run_folder}")
async def download_run_folder(run_folder: str):
    run_path = os.path.join(settings.OUTPUT_DIR, run_folder)

    if not os.path.exists(run_path) or not os.path.isdir(run_path):
        raise HTTPException(status_code=404, detail="运行目录不存在")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(run_path):
            for file in files:
                file_full_path = os.path.join(root, file)
                arcname = os.path.relpath(file_full_path, run_path)
                zipf.write(file_full_path, arcname)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type='application/zip',
        headers={"Content-Disposition": f"attachment; filename={run_folder}.zip"}
    )


@router.post("/open-output-dir")
async def open_output_directory():
    output_dir = os.path.abspath(settings.OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)

    try:
        sys_platform = platform.system()
        if sys_platform == 'Windows':
            os.startfile(output_dir)
        elif sys_platform == 'Darwin':
            subprocess.Popen(['open', output_dir])
        else:
            subprocess.Popen(['xdg-open', output_dir])

        return {"success": True, "message": f"已打开输出目录: {output_dir}", "path": output_dir}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"无法打开输出目录: {str(e)}")
