#!/bin/bash
set -e

JOBS=1

while test $# -gt 0; do
    case "$1" in
        --cmake)
            shift
            export CMAKE_EXEC=$1
            ;;
        --fakeroot)
            shift
            export FAKEROOT=$1
            ;;
        --jobs)
            shift
            export JOBS=$1
            ;;
        --prefix)
            shift
            export PREFIX=$1
            ;;
        --python)
            shift
            export PYTHON=$1
            ;;
        --ld-library-path)
            shift
            ;;
        *)
            export OPTS="$OPTS $1"
            ;;
    esac
    shift
done

cat <<EOF > name_mangling_patch.diff
patch="diff --git a/_posixsubprocess.c b/_posixsubprocess.c
index 012715e..d989634 100644
--- a/_posixsubprocess.c
+++ b/_posixsubprocess.c
@@ -876,7 +876,7 @@ static PyMethodDef module_methods[] = {
 
 
 PyMODINIT_FUNC
-init_posixsubprocess(void)
+init_posixsubprocess32(void)
 {
     PyObject *m;
 
@@ -886,7 +886,7 @@ init_posixsubprocess(void)
         return;
 #endif
 
-    m = Py_InitModule3("_posixsubprocess", module_methods, module_doc);
+    m = Py_InitModule3("_posixsubprocess32", module_methods, module_doc);
     if (m == NULL)
         return;
 }
diff --git a/setup.py b/setup.py
index da410c1..65edb59 100755
--- a/setup.py
+++ b/setup.py
@@ -10,7 +10,7 @@ def main():
         sys.stderr.write('This backport is for Python 2.x only.\n')
         sys.exit(1)
 
-    ext = Extension('_posixsubprocess', ['_posixsubprocess.c'],
+    ext = Extension('_posixsubprocess32', ['_posixsubprocess.c'],
                     depends=['_posixsubprocess_helpers.c'])
     if os.name == 'posix':
         ext_modules = [ext]
diff --git a/subprocess32.py b/subprocess32.py
index f1522c0..ab61d8f 100644
--- a/subprocess32.py
+++ b/subprocess32.py
@@ -463,7 +463,7 @@ else:
     import pickle
 
     try:
-        import _posixsubprocess
+        import _posixsubprocess32 as _posixsubprocess
     except ImportError:
         _posixsubprocess = None
         import warnings
diff --git a/test_subprocess32.py b/test_subprocess32.py
index c312949..4ba2024 100644
--- a/test_subprocess32.py
+++ b/test_subprocess32.py
@@ -1975,7 +1975,7 @@ class ProcessTestCasePOSIXPurePython(ProcessTestCase, POSIXProcessTestCase):
         POSIXProcessTestCase.setUp(self)
 
     def tearDown(self):
-        subprocess._posixsubprocess = sys.modules['_posixsubprocess']
+        subprocess._posixsubprocess = sys.modules['_posixsubprocess32']
         POSIXProcessTestCase.tearDown(self)
         ProcessTestCase.tearDown(self)
 
EOF

git apply name_mangling_patch.diff
python setup.py install --prefix=$PREFIX $OPTS
