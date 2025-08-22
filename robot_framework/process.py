"""This module contains the main process of the robot."""

import os
import sys
import time
import logging
import subprocess
import shutil
import platform
import getpass
from pathlib import Path

from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection
from OpenOrchestrator.database.queues import QueueElement


# pylint: disable-next=unused-argument
def process(orchestrator_connection: OrchestratorConnection, queue_element: QueueElement | None = None) -> None:
    """Do the primary process of the robot."""
    print("HEY!!!!!")
    orchestrator_connection.log_trace("Running process.")
    
    # ---------- Paths & constants ----------
    ROOT = Path(__file__).resolve().parent
    VENV_DIR = ROOT / ".venv"
    THIS_FILE = Path(__file__).resolve()
    REQ_FILE = ROOT / "requirements.txt"
    IN_VENV = os.environ.get("IN_VENV") == "1"
    ON_WINDOWS = os.name == "nt"
    
    def venv_python_path(venv_dir: Path) -> Path:
        return venv_dir / ("Scripts/python.exe" if ON_WINDOWS else "bin/python")
    
    # ---------- Audit log ----------
    LOG_FILE = str(ROOT / "script_audit.log")
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    logging.getLogger().addHandler(console)
    
    logging.info(
        "Script started. User=%s Machine=%s Python=%s CWD=%s InVenv=%s",
        getpass.getuser(), platform.node(), sys.version, os.getcwd(), IN_VENV
    )
    
    # ---------- Helpers ----------
    def safe_rmtree(path: Path, retries: int = 5, delay: float = 0.5):
        """Robustly delete a directory tree with retries (helps on Windows)."""
        for i in range(retries):
            try:
                if path.exists():
                    shutil.rmtree(path, ignore_errors=False)
                return
            except Exception as e:
                logging.warning("Attempt %s to delete %s failed: %s", i + 1, path, e)
                time.sleep(delay)
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass
        if path.exists():
            logging.warning("Could not fully remove %s; some files may remain.", path)
    
    def run_py_in_venv(args, env=None):
        """
        Run `<venv python> args...` and raise on failure.
        Example: run_py_in_venv(["-m", "pip", "install", "-r", "requirements.txt"])
        """
        vpy = str(venv_python_path(VENV_DIR))
        full = [vpy] + args
        logging.info("Running: %s", " ".join(full))
        subprocess.check_call(full, env=env)
    
    def bootstrap_and_reexec():
        """Create venv, install deps, then re-run this script inside it. Clean up venv afterwards."""
        created = False
        try:
            # 1) Create venv if missing
            if not VENV_DIR.exists():
                logging.info("Creating virtual environment at %s", VENV_DIR)
                subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])
                created = True
            else:
                logging.info("Virtual environment already exists at %s", VENV_DIR)
    
            # Prepare env (avoid pip version check noise)
            pip_env = os.environ.copy()
            pip_env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    
            # 2) Upgrade pip/wheel/setuptools via `python -m pip` (preferred on 3.13+)
            try:
                logging.info("Upgrading pip in venv (python -m pip)…")
                run_py_in_venv(["-m", "pip", "install", "--upgrade", "pip", "wheel", "setuptools"], env=pip_env)
            except subprocess.CalledProcessError as e:
                logging.warning("pip upgrade failed (continuing): %s", e)
    
            # 3) Install from requirements.txt if present
            if REQ_FILE.exists():
                logging.info("Installing requirements from %s", REQ_FILE)
                run_py_in_venv(["-m", "pip", "install", "-r", str(REQ_FILE)], env=pip_env)
            else:
                logging.warning("No requirements.txt found at %s; continuing without installs.", REQ_FILE)
    
            # 4) Re-run this script using the venv's Python
            vpy = str(venv_python_path(VENV_DIR))
            logging.info("Re-launching script inside venv: %s", vpy)
            env = os.environ.copy()
            env["IN_VENV"] = "1"
            args = [vpy, str(THIS_FILE), *sys.argv[1:]]
            result = subprocess.call(args, env=env)
            logging.info("Inner run exited with code %s", result)
            exit_code = result
        except subprocess.CalledProcessError as e:
            logging.exception("Bootstrap failed: %s", e)
            exit_code = e.returncode if hasattr(e, "returncode") else 1
        finally:
            # 5) Delete venv after inner run or bootstrap failure
            if VENV_DIR.exists():
                logging.info("Removing virtual environment at %s", VENV_DIR)
                safe_rmtree(VENV_DIR)
            elif created:
                logging.info("Venv was created but no longer exists at cleanup time.")
        sys.exit(exit_code)
    
    # ---------- Bootstrap phase (outer) ----------
    if not IN_VENV:
        bootstrap_and_reexec()
    
    # ---------- Main logic (runs INSIDE the venv) ----------
    def is_headless():
        try:
            import ctypes
            user32 = ctypes.windll.user32
            return user32.GetSystemMetrics(0) == 0 or user32.GetSystemMetrics(1) == 0
        except Exception:
            return True
    
    HEADLESS = os.environ.get("FORCE_HEADLESS") == "1" or is_headless()
    
    if HEADLESS:
        logging.warning("No interactive desktop detected. Using headless fallback.")
        out = os.path.abspath("hello_world.txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write("Hello World")
        logging.info("Wrote %s", out)
        logging.info("Finished (headless). Log: %s", LOG_FILE)
        sys.exit(0)
    
    # ---------- Import pyautogui (installed in venv) ----------
    try:
        import pyautogui
    except ImportError:
        logging.error("pyautogui is not installed in the venv. "
                      "Make sure requirements.txt includes 'pyautogui'.")
        sys.exit(1)
    
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    
    # ---------- Launch Notepad ----------
    try:
        logging.info("Launching Notepad...")
        subprocess.Popen(["notepad.exe"])
    except FileNotFoundError:
        logging.error("Could not launch Notepad on this system.")
        sys.exit(1)
    
    time.sleep(5)
    
    try:
        logging.info("Typing 'Hello World'...")
        pyautogui.write("Hello World", interval=0.20)
        logging.info("Done typing.")
    except Exception as e:
        logging.exception("Typing failed: %s", e)
        sys.exit(1)
    
    logging.info("Finished. Log: %s", LOG_FILE)
