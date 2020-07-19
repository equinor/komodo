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
        *)
            export OPTS="$OPTS $1"
            ;;
    esac
    shift
done


# Patch for PySide2 that allows building without docs (building docs would require sphinx)
NO_DOCS_PATCH="diff --git a/setup.py b/setup.py
index ef3a1a7..8f6ac21 100644
--- a/setup.py
+++ b/setup.py
@@ -227,6 +227,7 @@ OPTION_LISTVERSIONS = has_option(\"list-versions\")
 OPTION_MAKESPEC = option_value(\"make-spec\")
 OPTION_IGNOREGIT = has_option(\"ignore-git\")
 OPTION_NOEXAMPLES = has_option(\"no-examples\")     # don't include pyside2-examples
+OPTION_NO_DOCS = has_option(\"no-docs\")            # don't build documentation
 OPTION_JOBS = option_value('jobs')                # number of parallel build jobs
 OPTION_JOM = has_option('jom')                    # Legacy, not used any more.
 OPTION_NO_JOM = has_option('no-jom')              # Do not use jom instead of nmake with msvc
@@ -829,6 +830,9 @@ class pyside_build(_build):
         cmake_cmd.append(\"-DPYTHON_EXECUTABLE=%s\" % self.py_executable)
         cmake_cmd.append(\"-DPYTHON_INCLUDE_DIR=%s\" % self.py_include_dir)
         cmake_cmd.append(\"-DPYTHON_LIBRARY=%s\" % self.py_library)
+        if OPTION_NO_DOCS:
+            cmake_cmd.append(\"-DNO_DOCS=ON\")
+
         # Add source location for generating documentation
         if qtSrcDir:
             cmake_cmd.append(\"-DQT_SRC_DIR=%s\" % qtSrcDir)
@@ -878,7 +882,7 @@ class pyside_build(_build):
         if run_process(cmd_make) != 0:
             raise DistutilsSetupError(\"Error compiling \" + extension)
 
-        if extension.lower() == \"shiboken2\":
+        if extension.lower() == \"shiboken2\" and not OPTION_NO_DOCS:
             log.info(\"Generating Shiboken documentation %s...\" % extension)
             if run_process([self.make_path, \"doc\"]) != 0:
                 raise DistutilsSetupError(\"Error generating documentation \" + extension)
diff --git a/sources/pyside2/CMakeLists.txt b/sources/pyside2/CMakeLists.txt
index caf400d..d4bb023 100644
--- a/sources/pyside2/CMakeLists.txt
+++ b/sources/pyside2/CMakeLists.txt
@@ -416,15 +416,18 @@ endif()
 add_subdirectory(PySide2)
 if (BUILD_TESTS)
     enable_testing()
-    add_subdirectory(tests)				
+    add_subdirectory(tests)
 endif ()
 
 find_program(SPHINX_BUILD sphinx-build)
 find_program(DOT_EXEC dot)
 
-if (QT_SRC_DIR AND SPHINX_BUILD AND DOT_EXEC)
+if (NO_DOCS)
+  message(STATUS \"NO_DOCS option specified, apidoc generation targets disabled\")
+else()
+  if (QT_SRC_DIR AND SPHINX_BUILD AND DOT_EXEC)
     add_subdirectory(doc)
-else ()
+  else()
     set(DOCS_TARGET_DISABLED_MESSAGE \"apidoc generation targets disabled.\")
     if (NOT QT_SRC_DIR)
         message(STATUS \"QT_SRC_DIR variable not set, \${DOCS_TARGET_DISABLED_MESSAGE}\")
@@ -432,7 +435,10 @@ else()
         message(STATUS \"sphinx-build command not found, \${DOCS_TARGET_DISABLED_MESSAGE}\")
     elseif (NOT DOT_EXEC)
         message(STATUS \"graphviz not found, \${DOCS_TARGET_DISABLED_MESSAGE}\")
+      elseif (NO_DOCS)
+
     else()
         message(STATUS \"Unknown issue occurred, \${DOCS_TARGET_DISABLED_MESSAGE}\")
     endif()
+  endif()
 endif()
diff --git a/sources/shiboken2/CMakeLists.txt b/sources/shiboken2/CMakeLists.txt
index 94172c1..06b9517 100644
--- a/sources/shiboken2/CMakeLists.txt
+++ b/sources/shiboken2/CMakeLists.txt
@@ -320,7 +320,12 @@ else()
 endif()
 
 add_subdirectory(libshiboken)
-add_subdirectory(doc)
+
+if(NO_DOCS)
+  message(STATUS \"NO_DOCS option specified, shiboken2 documentation will not be generated\")
+else()
+  add_subdirectory(doc)
+endif()
 
 # deps found, compile the generator.
 if (Qt5Core_FOUND AND PYTHONINTERP_FOUND)"

echo "$NO_DOCS_PATCH" > no_docs_patch.patch
git apply --ignore-space-change --ignore-whitespace no_docs_patch.patch


# Get libclang (required only for building)
# Jenkins seems to have the uppercase version, while wget wants the lowercase version
export http_proxy=http://www-proxy.statoil.no:80
wget --quiet http://download.qt.io/development_releases/prebuilt/libclang/libclang-release_40-linux-Rhel6.6-gcc4.9-x86_64.7z -O libclang-4.0.7z

rm -rf libclang
7za x libclang-4.0.7z -o"$(pwd)"
export LLVM_INSTALL_DIR="$(pwd)/libclang"

export PYTHONHOME="$(dirname $(dirname $(which python)))"

# Build & install PySide
python setup.py install -O2 --ignore-git --no-docs --jobs=$JOBS --cmake=$CMAKE_EXEC --prefix=$PREFIX $OPTS

