import sqlite3
import os
import json
from fastapi import APIRouter, Request, UploadFile, File, Depends, HTTPException, status, Form, Body
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.core.config import settings
from app.api.deps import get_db
from app.services import file_service, xmind_service

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(settings.APP_DIR, "templates"))

def fetch_configs(db: sqlite3.Connection):
    """从数据库读取全局配置并打包成字典，同时同步项目到数据库"""
    cursor = db.cursor()
    cursor.execute("SELECT key, value FROM configs")
    rows = cursor.fetchall()
    configs = {row['key']: row['value'] for row in rows}
    
    # --- 全局双向同步逻辑 ---
    # 1. 确保配置中的项目在 projects 表中存在 (Config -> Table)
    project_names_in_config = [p.strip() for p in configs.get('projects', '').split(',') if p.strip()]
    for name in project_names_in_config:
        cursor.execute("SELECT id FROM projects WHERE name = ? AND is_deleted = 0", (name,))
        if not cursor.fetchone():
            from datetime import datetime
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO projects (name, create_on) VALUES (?, ?)", (name, now))
    
    # 2. 确保表中的项目在配置字符串中也存在 (Table -> Config)
    # 这样系统配置页面的“标签管理”就能看到所有存量项目
    cursor.execute("SELECT name FROM projects WHERE is_deleted = 0")
    db_project_names = [row[0] for row in cursor.fetchall()]
    
    # 合并并更新配置
    all_projects = sorted(list(set(project_names_in_config) | set(db_project_names)))
    new_projects_str = ",".join(all_projects)
    
    if configs.get('projects') != new_projects_str:
        cursor.execute("INSERT OR REPLACE INTO configs (key, value) VALUES (?, ?)", ('projects', new_projects_str))
        configs['projects'] = new_projects_str
    
    db.commit()
    # ----------------------

    # 动态覆盖 settings 中的开关，确保模板逻辑一致
    class DynamicSettings:
        def __init__(self, configs):
            self.ENABLE_ZENTAO = configs.get('enable_zentao', '1') == '1'
            self.ENABLE_TESTLINK = configs.get('enable_testlink', '1') == '1'
            self.UPLOAD_FOLDER = settings.UPLOAD_FOLDER
            self.DEBUG = settings.DEBUG
            self.APP_DIR = settings.APP_DIR
            
    return configs, DynamicSettings(configs)

@router.get("/configs", response_class=HTMLResponse, name="manage_configs")
async def manage_configs(request: Request, db: sqlite3.Connection = Depends(get_db)):
    configs, _ = fetch_configs(db)
    return templates.TemplateResponse("configs.html", {"request": request, "configs": configs})

@router.post("/api/configs")
async def update_configs(data: dict = Body(...), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    try:
        # 1. 更新配置表
        for key, value in data.items():
            cursor.execute("INSERT OR REPLACE INTO configs (key, value) VALUES (?, ?)", (key, str(value)))
        
        # 2. 增强的项目同步与删除校验逻辑
        new_project_names_str = data.get('projects', '')
        new_project_names = set([p.strip() for p in new_project_names_str.split(',') if p.strip()])
        
        # 获取当前库中存量项目
        cursor.execute("SELECT id, name FROM projects WHERE is_deleted = 0")
        current_projects = {row[1]: row[0] for row in cursor.fetchall()} # name -> id
        
        # 2.1 校验：寻找被移除的项目，检查是否有绑定数据
        removed_projects = set(current_projects.keys()) - new_project_names
        for p_name in removed_projects:
            p_id = current_projects[p_name]
            cursor.execute("SELECT COUNT(*) FROM records WHERE project_id = ?", (p_id,))
            record_count = cursor.fetchone()[0]
            if record_count > 0:
                raise HTTPException(
                    status_code=400, 
                    detail=f"保存失败：项目 “{p_name}” 下仍有 {record_count} 条测试记录，不能直接从配置中移除。请先删除相关记录。"
                )
            else:
                # 安全移除：如果没有数据，则在保存配置时同步将其标记为 soft delete
                cursor.execute("UPDATE projects SET is_deleted = 1 WHERE id = ?", (p_id,))

        # 2.2 同步：添加新项目
        for name in new_project_names:
            if name not in current_projects:
                from datetime import datetime
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("INSERT INTO projects (name, create_on) VALUES (?, ?)", (name, now))
        
        db.commit()
        return {"status": "success"}
    except HTTPException as he:
        db.rollback()
        raise he
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.get("/", response_class=HTMLResponse, name="index")
def index(request: Request, db: sqlite3.Connection = Depends(get_db)):
    records = file_service.get_records(db)
    configs, dyn_settings = fetch_configs(db)
    
    configs, dyn_settings = fetch_configs(db)
    
    # 从数据库获取同步后的项目列表（用于下拉）
    cursor = db.cursor()
    cursor.execute("SELECT id, name FROM projects WHERE is_deleted = 0 ORDER BY id DESC")
    projects = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
            
    case_types = [c.strip() for c in configs.get('case_types', '').split(',') if c.strip()]
    apply_phases = [p.strip() for p in configs.get('apply_phases', '').split(',') if p.strip()]

    # Calculate statistics
    from datetime import datetime, timedelta
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM records WHERE DATE(create_on) = ?", (today,))
    today_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM records WHERE DATE(create_on) >= ?", (week_ago,))
    week_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM records")
    total_records = cursor.fetchone()[0]
    
    stats = {
        "today_count": today_count,
        "week_count": week_count,
        "total_records": total_records
    }
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "records": records,
        "projects": projects,
        "case_types": case_types,
        "apply_phases": apply_phases,
        "stats": stats,
        "settings": dyn_settings
    })

@router.api_route("/index", methods=["GET", "POST"], response_class=HTMLResponse)
async def index_redirect(
    request: Request, 
    db: sqlite3.Connection = Depends(get_db),
    file: UploadFile = File(None),
    project_id: int = Form(None),
    case_type: str = Form("功能测试"),
    apply_phase: str = Form("功能测试阶段")
):
    """处理 /index 路由（支持 GET 和 POST）"""
    if request.method == "POST":
        # 调用上传处理函数
        return upload_file(request, file, project_id, db, case_type, apply_phase)
    else:
        # GET 请求，显示首页
        return index(request, db)

@router.get("/favicon.ico")
async def favicon():
    """返回 favicon（避免 404 错误）"""
    from fastapi.responses import Response
    # 返回一个空的 1x1 透明 PNG
    return Response(
        content=b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82',
        media_type="image/png"
    )



@router.get("/projects", response_class=HTMLResponse, name="manage_projects")
def manage_projects(request: Request, db: sqlite3.Connection = Depends(get_db)):
    # 确保项目同步
    configs, dyn_settings = fetch_configs(db)
    
    cursor = db.cursor()
    cursor.execute("SELECT id, name, description, create_on FROM projects WHERE is_deleted = 0 ORDER BY id DESC")
    projects = [
        {"id": row[0], "name": row[1], "description": row[2], "create_on": row[3]}
        for row in cursor.fetchall()
    ]
    return templates.TemplateResponse("projects.html", {
        "request": request, 
        "projects": projects,
        "settings": dyn_settings
    })

@router.get("/projects/{project_id}", response_class=HTMLResponse, name="project_detail")
def project_detail(request: Request, project_id: int, db: sqlite3.Connection = Depends(get_db)):
    configs, dyn_settings = fetch_configs(db)
    
    cursor = db.cursor()
    cursor.execute("SELECT name, description FROM projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    project_name = row[0] if row else f"Project {project_id}"
    project_desc = row[1] if row else None
    
    project = {"id": project_id, "name": project_name, "description": project_desc}
    records = file_service.get_records(db, project_id=project_id)
    
    case_types = [c.strip() for c in configs.get('case_types', '').split(',') if c.strip()]
    apply_phases = [p.strip() for p in configs.get('apply_phases', '').split(',') if p.strip()]
    
    return templates.TemplateResponse("project_detail.html", {
        "request": request,
        "project": project,
        "records": records,
        "case_types": case_types,
        "apply_phases": apply_phases,
        "settings": dyn_settings
    })

@router.post("/", response_class=HTMLResponse)
def upload_file(
    request: Request, 
    file: UploadFile = File(...), 
    project_id: int = Form(None),
    db: sqlite3.Connection = Depends(get_db),
    case_type: str = Form("功能测试"),
    apply_phase: str = Form("功能测试阶段")
):
    if not project_id:
        # 重复逻辑，为了显示错误
        return index(request, db)

    filename, error = file_service.save_file(file, db, project_id, case_type=case_type, apply_phase=apply_phase)
    if filename:
        file_service.delete_records_keep_latest(db)
        return RedirectResponse(url=f"/preview/{filename}", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return index(request, db)

@router.get("/preview/id/{record_id}", response_class=HTMLResponse, name="preview_record")
def preview_record(request: Request, record_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, name, content, project_id FROM records WHERE id = ? AND is_deleted <> 1", (record_id,))
    record = cursor.fetchone()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    testcases = []
    # record is likely sqlite3.Row, but index access is safer if dict access is suspect
    db_content = record[2] 
    record_name = record[1]
    
    if db_content:
        try:
            testcases = json.loads(db_content)
        except Exception as e:
            # Fallback to file parsing if DB content is corrupt
            print(f"Error loading JSON for record {record_id}. Type: {type(db_content)}, Error: {e}")
            testcases = xmind_service.get_testcases(record_name)
    else:
        testcases = xmind_service.get_testcases(record_name)

    # suite_count 统计
    testsuites = xmind_service.get_testsuites(record_name)
    suite_count = sum(len(suite.sub_suites) for suite in testsuites) if testsuites else 0
    
    _, dyn_settings = fetch_configs(db)

    response = templates.TemplateResponse('preview.html', {
        "request": request, 
        "name": record_name, 
        "suite": testcases, 
        "suite_count": suite_count,
        "record_id": record[0],
        "project_id": record[3],
        "settings": dyn_settings
    })
    # Disable caching to ensure fresh data on reload
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@router.get("/preview/{filename}", response_class=HTMLResponse, name="preview_file")
def preview_file(request: Request, filename: str, db: sqlite3.Connection = Depends(get_db)):
    # Redirect to ID-based preview if record exists
    record = file_service.get_record_by_filename(db, filename)
    if record:
        return RedirectResponse(url=f"/preview/id/{record['id']}")
        
    full_path = os.path.join(settings.UPLOAD_FOLDER, filename)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    testcases = xmind_service.get_testcases(filename)
    testsuites = xmind_service.get_testsuites(filename)
    suite_count = sum(len(suite.sub_suites) for suite in testsuites) if testsuites else 0
    
    _, dyn_settings = fetch_configs(db)

    return templates.TemplateResponse('preview.html', {
        "request": request, 
        "name": filename, 
        "suite": testcases, 
        "suite_count": suite_count,
        "record_id": None,
        "project_id": None,
        "settings": dyn_settings
    })

@router.get("/delete/{filename}/{record_id}", name="delete_file")
def delete_file(filename: str, record_id: int, db: sqlite3.Connection = Depends(get_db)):
    file_service.delete_record(filename, record_id, db)
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/api/download-all")
async def download_all(request: Request):
    """Download all file formats (XMind, CSV, XML) as a ZIP"""
    import zipfile
    import io
    from fastapi.responses import StreamingResponse
    
    form_data = await request.form()
    filename = form_data.get("filename")
    
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    # Prepare file paths
    xmind_path = os.path.join(settings.UPLOAD_FOLDER, filename)
    csv_path = os.path.join(settings.UPLOAD_FOLDER, filename.replace('.xmind', '.csv'))
    xml_path = os.path.join(settings.UPLOAD_FOLDER, filename.replace('.xmind', '.xml'))
    
    # Create ZIP file in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add XMind file
        if os.path.exists(xmind_path):
            zip_file.write(xmind_path, os.path.basename(xmind_path))
        
        # Add CSV file
        if os.path.exists(csv_path):
            zip_file.write(csv_path, os.path.basename(csv_path))
        
        # Add XML file
        if os.path.exists(xml_path):
            zip_file.write(xml_path, os.path.basename(xml_path))
    
    zip_buffer.seek(0)
    
    # Return ZIP file
    zip_filename = filename.replace('.xmind', '_all_formats.zip')
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
    )
