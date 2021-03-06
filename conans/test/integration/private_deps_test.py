import unittest
from conans.test.tools import TestClient, TestServer
from conans.model.ref import ConanFileReference
import platform
import os
from conans.test.utils.cpp_test_files import cpp_hello_conan_files
from conans.paths import CONANFILE, BUILD_INFO, CONANINFO, BUILD_INFO_CMAKE
from conans.util.files import load
from conans.model.info import ConanInfo
from conans.model.build_info import DepsCppInfo
from nose.plugins.attrib import attr


@attr("slow")
class PrivateDepsTest(unittest.TestCase):

    def setUp(self):
        test_server = TestServer([("*/*@*/*", "*")],  # read permissions
                                 [],  # write permissions
                                 users={"lasote": "mypass"})  # exported users and passwords
        self.servers = {"default": test_server}
        self.client = TestClient(servers=self.servers, users=[("lasote", "mypass")])

    def _export_upload(self, name=0, version=None, deps=None, msg=None, static=True):
        dll_export = self.client.default_compiler_visual_studio and not static
        files = cpp_hello_conan_files(name, version, deps, msg=msg, static=static,
                                      private_includes=True, dll_export=dll_export)
        conan_ref = ConanFileReference(name, version, "lasote", "stable")
        self.client.save(files, clean_first=True)
        self.client.run("export lasote/stable")
        self.client.run("upload %s" % str(conan_ref))

    def reuse_test(self):
        self._export_upload("Hello0", "0.1")
        self._export_upload("Hello00", "0.2", msg="#")
        self._export_upload("Hello1", "0.1", deps=[("Hello0/0.1@lasote/stable", "private")],
                            static=False)
        self._export_upload("Hello2", "0.1", deps=[("Hello00/0.2@lasote/stable", "private")],
                            static=False)

        client = TestClient(servers=self.servers, users=[("lasote", "mypass")])  # Mocked userio
        files3 = cpp_hello_conan_files("Hello3", "0.1", ["Hello1/0.1@lasote/stable",
                                                        "Hello2/0.1@lasote/stable"])

        # WE need to copy the DLLs and dylib
        local_install = """    def imports(self):
        self.copy("*.dll", "", "bin")
        self.copy("*.dylib", "", "lib")
"""
        copy_dlls_conanfile = files3[CONANFILE] + local_install
        files3[CONANFILE] = copy_dlls_conanfile
        client.save(files3)

        client.run('install --build missing')
        client.run('build')

        # assert Hello3 only depends on Hello2, and Hello1
        info_path = os.path.join(client.current_folder, BUILD_INFO_CMAKE)
        build_info_cmake = load(info_path)
        # Ensure it does not depend on Hello0 to build, as private in dlls
        self.assertNotIn("Hello0", repr(build_info_cmake))

        command = os.sep.join([".", "bin", "say_hello"])
        client.runner(command, client.current_folder)
        self.assertEqual(['Hello Hello3', 'Hello Hello1', 'Hello Hello0', 'Hello Hello2',
                          'Hello #'],
                         str(client.user_io.out).splitlines()[-5:])

        # assert Hello3 only depends on Hello2, and Hello1
        info_path = os.path.join(client.current_folder, CONANINFO)
        conan_info = ConanInfo.loads(load(info_path))

        self.assertEqual("language=0\nstatic=True", conan_info.options.dumps())

        # Try to upload and reuse the binaries
        client.run("upload Hello1/0.1@lasote/stable --all")
        self.assertEqual(str(client.user_io.out).count("Uploading package"), 1)
        client.run("upload Hello2/0.1@lasote/stable --all")
        self.assertEqual(str(client.user_io.out).count("Uploading package"), 1)

        client2 = TestClient(servers=self.servers, users=[("lasote", "mypass")])
        files2 = cpp_hello_conan_files("Hello3", "0.1", ["Hello1/0.1@lasote/stable",
                                                          "Hello2/0.1@lasote/stable"])

        # WE need to copy the DLLs
        copy_dlls_conanfile = files2[CONANFILE] + local_install
        files2[CONANFILE] = copy_dlls_conanfile
        client2.save(files2)

        client2.run("install . --build missing")
        self.assertNotIn("Package installed in Hello0/0.1", client2.user_io.out)
        self.assertNotIn("Building", client2.user_io.out)
        client2.run("build .")

        self.assertNotIn("libhello0.a", client2.user_io.out)
        self.assertNotIn("libhello00.a", client2.user_io.out)
        self.assertNotIn("libhello1.a", client2.user_io.out)
        self.assertNotIn("libhello2.a", client2.user_io.out)
        self.assertNotIn("libhello3.a", client2.user_io.out)
        client2.runner(command, client2.current_folder)

        self.assertEqual(['Hello Hello3', 'Hello Hello1', 'Hello Hello0', 'Hello Hello2',
                          'Hello #'],
                         str(client2.user_io.out).splitlines()[-5:])
        files3 = cpp_hello_conan_files("Hello3", "0.2", ["Hello1/0.1@lasote/stable",
                                                          "Hello2/0.1@lasote/stable"], language=1)

        copy_dlls_conanfile = files3[CONANFILE] + local_install
        files3[CONANFILE] = copy_dlls_conanfile
        client2.save(files3)
        client2.run('install -o language=1 --build missing')
        client2.run('build')
        self.assertNotIn("libhello0.a", client2.user_io.out)
        self.assertNotIn("libhello00.a", client2.user_io.out)
        self.assertNotIn("libhello1.a", client2.user_io.out)
        self.assertNotIn("libhello2.a", client2.user_io.out)
        self.assertNotIn("libhello3.a", client2.user_io.out)
        client2.runner(command, client2.current_folder)
        self.assertEqual(['Hola Hello3', 'Hola Hello1',
                          'Hola Hello0', 'Hola Hello2', 'Hola #'],
                         str(client2.user_io.out).splitlines()[-5:])
