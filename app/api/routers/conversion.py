import os
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from app.core.config import settings
from app.api.deps import get_db
from fastapi import Depends
from app.services import file_service, xmind_service

from urllib.parse import quote

router = APIRouter()

@router.get("/uploads/{filename}", name="uploaded_file")
def download_uploaded_file(filename: str):
    file_path = os.path.join(settings.UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

@router.get("/{filename}/to/testlink", name="download_testlink_file")
def download_testlink_file(filename: str, cases: str = Query(None), db=Depends(get_db)):
    record = file_service.get_record_by_filename(db, filename)
    testsuites = None
    if record and record['content']:
        import json
        try:
            testcases = json.loads(record['content'])
            
            # Filter by cases (indices) if provided
            if cases:
                indices = [int(i) for i in cases.split(',') if i.strip().isdigit()]
                testcases = [testcases[i] for i in indices if 0 <= i < len(testcases)]
                
            root_name = os.path.splitext(filename)[0]
            testsuites = xmind_service.reconstruct_testsuites_from_db_list(testcases, root_name=root_name)
        except:
            pass
            
    result_file = xmind_service.convert_to_testlink(filename, testsuites=testsuites)
    if not result_file:
         raise HTTPException(status_code=404, detail="Conversion failed or file not found")
    
    encoded_filename = quote(os.path.basename(result_file))
    return FileResponse(
        result_file, 
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
    )

@router.get("/{filename}/to/zentao", name="download_zentao_file")
def download_zentao_file(filename: str, cases: str = Query(None), db=Depends(get_db)):
    record = file_service.get_record_by_filename(db, filename)
    testcases = None
    case_type = None
    apply_phase = None
    if record:
        case_type = record.get('case_type')
        apply_phase = record.get('apply_phase')
        if record.get('content'):
            import json
            try:
                testcases = json.loads(record['content'])
                
                # Filter by cases (indices) if provided
                if cases:
                    indices = [int(i) for i in cases.split(',') if i.strip().isdigit()]
                    testcases = [testcases[i] for i in indices if 0 <= i < len(testcases)]
            except:
                pass

    result_file = xmind_service.convert_to_zentao(filename, testcases=testcases, case_type=case_type, apply_phase=apply_phase)
    if not result_file:
        raise HTTPException(status_code=404, detail="Conversion failed or file not found")
        
    encoded_filename = quote(os.path.basename(result_file))
    return FileResponse(
        result_file, 
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
    )

@router.get("/{filename}/to/xmind", name="download_xmind_file")
def download_xmind_file(filename: str, cases: str = Query(None), db=Depends(get_db)):
    record = file_service.get_record_by_filename(db, filename)
    testsuites = None
    if record and record['content']:
        import json
        try:
            testcases = json.loads(record['content'])
            
            # Filter by cases (indices) if provided
            if cases:
                indices = [int(i) for i in cases.split(',') if i.strip().isdigit()]
                testcases = [testcases[i] for i in indices if 0 <= i < len(testcases)]
                
            root_name = os.path.splitext(filename)[0]
            testsuites = xmind_service.reconstruct_testsuites_from_db_list(testcases, root_name=root_name)
        except:
            pass

    xmind_stream = xmind_service.convert_to_xmind(filename, testsuites=testsuites)
    if not xmind_stream:
        # Fallback if no DB content or conversion fails? 
        # Actually xmind_service.convert_to_xmind only works with testsuites.
        raise HTTPException(status_code=404, detail="Conversion failed or no data found")
        
    # Return stream as file
    from fastapi.responses import StreamingResponse
    encoded_filename = quote(filename)
    return StreamingResponse(
        xmind_stream, 
        media_type="application/zip", 
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
    )
