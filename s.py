import scipy
def check_scipy_version():
   version = scipy.__version__
   print(f"SciPy version: {version}")
if __name__ == "__main__":
   check_scipy_version()