@echo off
setlocal
cd /d "%~dp0"
set "HF_HUB_OFFLINE=1"
if not exist "results" mkdir "results"
echo STEP 1: Checking the BibTeX grammar. Tests should finish with OVERALL: PASS.
echo.
".venv\Scripts\python.exe" run_tests.py > "results\latest-tests.log" 2>&1
set "test_status=%errorlevel%"
type "results\latest-tests.log"
if not "%test_status%"=="0" goto failed
echo.
echo STEP 2: Asking the local model for three citations guided by SynCode.
echo This can take a few minutes. Leave this window open.
echo.
".venv\Scripts\python.exe" -u bibtex_syncode.py --revision 7ae557604adf67be50417f59c2c2f167def9a775 --output results/latest-demo.json > "results\latest-generation.log" 2>&1
set "generation_status=%errorlevel%"
type "results\latest-generation.log"
if not "%generation_status%"=="0" goto failed
echo.
echo DEMONSTRATION COMPLETE. All constrained outputs passed syntax validation.
echo The model's publication details have not been checked for accuracy.
echo Results are saved in results\latest-demo.json.
echo.
if /I not "%~1"=="--no-pause" pause
exit /b 0

:failed
echo.
echo A required check failed. Details are saved in the results folder.
echo Codex can inspect those logs directly; no copying between apps is needed.
echo.
if /I not "%~1"=="--no-pause" pause
exit /b 1
