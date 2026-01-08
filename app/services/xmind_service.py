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
    """Reconstruct a TestSuite hierarchy from flat list of test cases.
    
    The function parses hierarchical test case names (e.g., "Suite > Module > Case")
    and rebuilds the original tree structure with nested TestSuite objects.
    """
    import logging
    
    
    if not testcase_list:
        root_suite = TestSuite()
        root_suite.name = root_name
        root_suite.sub_suites = []
        return [root_suite]
    
    # Valid separators as defined in parser.py config
    valid_separators = ['>', '-', '&', '+', '/']
    
    # Auto-detect separator from the first test case
    detected_sep = None
    sample_name = testcase_list[0].get('name', '')
    logging.info(f"🔍 Detecting separator from sample: {sample_name}")
    for sep in valid_separators:
        # Check with spaces around separator (as parser adds them)
        if f' {sep} ' in sample_name:
            detected_sep = f' {sep} '
            break
    
    # Fallback to ' - ' if no separator detected
    if not detected_sep:
        detected_sep = ' - '
    
    logging.info(f"✅ Detected separator: '{detected_sep}'")
    
    suites_map = {}  # Mapping suite_name -> TestSuite
    
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
        
        # Parse hierarchical name
        full_name = case_dict.get('name', 'No Name')
        
        # Split by detected separator
        parts = full_name.split(detected_sep)
        parts = [p.strip() for p in parts if p.strip()]  # Clean up parts
        
        logging.debug(f"📋 Parsing '{full_name}' → parts: {parts}")
        
        if not parts:
            parts = [full_name]
        
        # Remove suite name from parts if it's the first part
        if parts and parts[0] == suite_name:
            parts = parts[1:]
            logging.debug(f"   Removed suite name, remaining: {parts}")
        
        if not parts:
            parts = ['Unnamed Case']
        
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
                # Ensure sub_suites is initialized
                if current_suite.sub_suites is None:
                    current_suite.sub_suites = []
                current_suite.sub_suites.append(found)
            
            current_suite = found
        
        # The actual test case
        case_name = parts[-1]
        logging.info(f"   ➡️ Creating TestCase: '{case_name}' (from parts {parts})")
        
        # Reconstruct TestCase object
        tc = TestCase()
        tc.name = case_name
        tc.version = 1
        tc.summary = case_dict.get('summary', '')
        tc.preconditions = case_dict.get('preconditions', '')
        tc.execution_type = 2 if case_dict.get('execution_type') in [2, '2', 'Automated'] else 1
        tc.tc_id = case_dict.get('tc_id', '')
        tc.importance = case_dict.get('importance', 2)
        tc.status = 7
        tc.result = case_dict.get('result', 0)
        tc.labels = case_dict.get('labels', [])
        
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

