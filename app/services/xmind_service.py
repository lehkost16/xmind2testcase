import os
import sys

# Ensure app/lib is in path for relative imports inside the libs if needed, 
# or just import directly if they are packages.
# Assuming xmind2testcase and xmindparser are packages in app/lib
from app.lib.xmind2testcase.utils import get_xmind_testsuites, get_xmind_testcase_list
from app.lib.xmind2testcase.testlink import xmind_to_testlink_xml_file
from app.lib.xmind2testcase.zentao import xmind_to_zentao_csv_file
from app.core.config import settings

def get_testsuites(filename: str):
    """Parse xmind file to get test suites."""
    full_path = os.path.join(settings.UPLOAD_FOLDER, filename)
    if not os.path.exists(full_path):
        return []
    return get_xmind_testsuites(full_path)

def get_testcases(filename: str):
    """Parse xmind file to get test cases."""
    full_path = os.path.join(settings.UPLOAD_FOLDER, filename)
    if not os.path.exists(full_path):
        return []
    return get_xmind_testcase_list(full_path)

def convert_to_testlink(filename: str, testsuites=None):
    """Convert xmind to TestLink XML."""
    full_path = os.path.join(settings.UPLOAD_FOLDER, filename)
    # Check path logic is handled in lib, but we pass full path
    return xmind_to_testlink_xml_file(full_path, testsuites=testsuites)

def convert_to_zentao(filename: str, testcases=None, case_type=None, apply_phase=None):
    """Convert xmind to ZenTao CSV."""
    full_path = os.path.join(settings.UPLOAD_FOLDER, filename)
    return xmind_to_zentao_csv_file(full_path, testcases=testcases, case_type=case_type, apply_phase=apply_phase)

from app.lib.xmind2testcase.metadata import TestSuite, TestCase, TestStep
from app.lib.xmind2testcase.writer import write_xmind_zip

def convert_to_xmind(filename: str, testsuites=None):
    """Convert DB testsuites to XMind file (BytesIO)."""
    if testsuites:
        return write_xmind_zip(testsuites)
    return None

def reconstruct_testsuites_from_db_list(testcase_list, root_name="Exported from XMind2TestCase"):
    """Reconstruct a TestSuite logic from flat list for TestLink export."""
    suites_map = {} # Mapping suite_name -> TestSuite
    
    for case_dict in testcase_list:
        suite_name = case_dict.get('suite', 'Default Suite')
        
        # Ensure root suite (Main Topic) exists
        if suite_name not in suites_map:
            ts = TestSuite()
            ts.name = suite_name
            ts.sub_suites = [] 
            ts.testcase_list = []
            suites_map[suite_name] = ts
        
        root_ts = suites_map[suite_name]
        
        # Unflatten Name to reconstruct hierarchy
        # Name format usually: "SuiteName - Module - Case" or "SuiteName Case"
        # We try to split by ' - ' first, then ' '.
        # Strategy: Remove suite_name from start if present.
        full_name = case_dict.get('name', 'No Name')
        
        # Normalize simple case where suite name is prefix
        clean_name = full_name
        if full_name.startswith(suite_name):
            # Strip suite name and potential separator
            clean_name = full_name[len(suite_name):].strip()
            for sep in ['- ', ' - ', ' ']:
                if clean_name.startswith(sep):
                    clean_name = clean_name[len(sep):].strip()
                    break
        
        # Now clean_name is "Module - Case" or just "Case"
        # Split into parts
        parts = []
        if ' - ' in clean_name:
            parts = clean_name.split(' - ')
        else:
            parts = [clean_name]
            
        # Traverse/Build hierarchy
        # The last part is the Case Name. The earlier parts are SubSuites.
        current_suite = root_ts
        
        for i, part in enumerate(parts[:-1]):
            # Find or create sub-suite
            found = None
            if current_suite.sub_suites:
                for sub in current_suite.sub_suites:
                    if sub.name == part:
                        found = sub
                        break
            
            if not found:
                found = TestSuite()
                found.name = part
                found.sub_suites = []
                found.testcase_list = []
                # Ensure sub_suites is initialized in metadata if None (class init defaults to None)
                if current_suite.sub_suites is None:
                    current_suite.sub_suites = []
                current_suite.sub_suites.append(found)
            
            current_suite = found
            
        # The actual case
        case_name = parts[-1]
        
        # Reconstruct TestCase object
        tc = TestCase()
        tc.name = case_name
        tc.version = 1
        tc.summary = case_dict.get('summary', '')
        tc.preconditions = case_dict.get('preconditions', '')
        tc.execution_type = 2 if case_dict.get('execution_type') in [2, '2', 'Automated'] else 1
        tc.importance = case_dict.get('importance', 2)
        tc.status = 7 
        tc.result = case_dict.get('result', 0)
        
        # Reconstruct Steps
        steps_data = case_dict.get('steps', [])
        tc.steps = []
        for i, s in enumerate(steps_data, 1):
            step = TestStep()
            step.step_number = i
            step.actions = s.get('actions', '')
            step.expectedresults = s.get('expectedresults', '')
            step.execution_type = 1
            tc.steps.append(step)
            
        if current_suite.testcase_list is None:
            current_suite.testcase_list = []
        current_suite.testcase_list.append(tc)
    
    # Wrap in a root suite
    root_suite = TestSuite()
    root_suite.name = root_name
    root_suite.sub_suites = list(suites_map.values())
    return [root_suite]
