"""Run the project's Python tests, whose filenames predate unittest discovery."""
import importlib.util,sys,unittest
from pathlib import Path
root=Path(__file__).resolve().parent
suite=unittest.TestSuite()
for i,name in enumerate(['server.test.py','exports.test.py','settings.test.py','settings-api.test.py','install.test.py']):
 spec=importlib.util.spec_from_file_location('watch_test_'+str(i),root/name)
 module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
 suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
if __name__=='__main__':sys.exit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
