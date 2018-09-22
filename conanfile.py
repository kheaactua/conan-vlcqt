#!/usr/bin/env python
# -*- coding: future_fstrings -*-
# -*- coding: utf-8 -*-

import os
from conans import ConanFile, CMake, tools


class VlcqtConan(ConanFile):
    """
    Note: The static build (on Windows) seems to fail when building the tests,
    as Qt is built into vlccore.lib, and the test libs
    """

    name            = 'vlcqt'
    version         = '1.1.1'
    license         = ''
    url             = 'https://github.com/kheaactua/conan-vlcqt'
    description     = 'Build VLC Qt'
    settings        = 'os', 'compiler', 'build_type', 'arch'
    options         = {'shared': [True, False]}
    default_options = 'shared=True'
    generators      = 'cmake'
    exports         = '*.patch'

    requires        = (
        'helpers/[>=0.3]@ntc/stable',
        'qt/[>=5.9.0]@ntc/stable',
    )

    def requirements(self):
        """ Definitely use conan vlc on Windows """
        if 'Windows' == self.settings.os:
            self.requires('vlc/3.0.3@ntc/stable')
        if 'Linux' == self.settings.os:
            if tools.os_info.os_version < '16':
                self.requires('vlc/[<3]@ntc/stable')
            else:
                self.requires('vlc/[>=3]@ntc/stable')

    def configure(self):
        qt_modules = (
            'qt3d',
            'qtbase',
            'qtcharts',
            'qtdatavis3d',
            'qtquickcontrols',
            'qtquickcontrols2',
            'qtsvg',
            'qtxmlpatterns',
            'qtcanvas3d',
        )

        for m in qt_modules: setattr(self.options['qt'], m, True)

    def source(self):
        self.run(f'git clone https://github.com/vlc-qt/vlc-qt.git {self.name}')
        self.run(f'cd {self.name} && git checkout {self.version}')

        # Fix the issue where it ignores and then destroys LIBVLC_BIN_DIR
        tools.patch(base_path=self.name, patch_file='cache.patch')

        if 'Windows' == self.settings.os:
            # Issue linking to VlcQmlPlayer.  See https://github.com/vlc-qt/vlc-qt/issues/173
            tools.replace_in_file(
                file_path=os.path.join(self.name, 'src', 'qml', 'QmlPlayer.h'),
                search ='class VlcQmlPlayer :',
                replace='class VLCQT_QML_EXPORT VlcQmlPlayer :',
                strict=True
            )

    def _set_up_cmake(self):
        # Import from helpers/x@ntc/stable
        from platform_helpers import adjustPath

        # Environment to perhaps populate
        env = {}

        cmake = CMake(self)

        cmake.definitions['STATIC'] = 'FALSE' if self.options.shared else 'TRUE'

        qt_deps = ['Core', 'Quick', 'Widgets', 'QuickTest']
        for p in qt_deps:
            cmake.definitions[f'Qt5{p}_DIR:PATH'] = adjustPath(os.path.join(self.deps_cpp_info['qt'].rootpath, 'lib', 'cmake', f'Qt5{p}'))
        cmake.definitions['QT_QMAKE_EXECUTABLE:PATH'] = adjustPath(os.path.join(self.deps_cpp_info['qt'].rootpath, 'bin', 'qmake'))
        if 'Windows' == self.settings.os:
            env['PATH'] = os.environ.get('PATH', '').split(';')
            env['PATH'].extend([adjustPath(os.path.join(self.deps_cpp_info['qt'].rootpath, p)) for p in ['bin']])

        if 'vlc' in self.deps_cpp_info.deps:
            def findLibInList(base, libs, name):
                """
                Search the list of libs for the one we want.
                On Windows, prefer the (shared) lib<lib>.lib to the <lib>.lib
                """
                test_lib = 'lib' + name
                if 'Windows' == self.settings.os:
                    test_lib = 'lib' + name + '.lib'
                else:
                    test_lib = 'lib' + name + '.so'
                test_lib = os.path.join(base, test_lib)
                test_lib = adjustPath(test_lib)
                if os.path.exists(test_lib):
                    return test_lib
                else:
                    raise ValueError('Could not find %s base=%s libs=%s'%(name, base, ', '.join(libs)))

            cmake.definitions['LIBVLC_LIBRARY:PATH']     = adjustPath(findLibInList(base=os.path.join(self.deps_cpp_info['vlc'].rootpath, self.deps_cpp_info['vlc'].libdirs[0]), libs=self.deps_cpp_info['vlc'].libs, name='vlc'))
            cmake.definitions['LIBVLCCORE_LIBRARY:PATH'] = adjustPath(findLibInList(base=os.path.join(self.deps_cpp_info['vlc'].rootpath, self.deps_cpp_info['vlc'].libdirs[0]), libs=self.deps_cpp_info['vlc'].libs, name='vlccore'))
            cmake.definitions['LIBVLC_INCLUDE_DIR:PATH'] = adjustPath(os.path.join(self.deps_cpp_info['vlc'].rootpath, self.deps_cpp_info['vlc'].includedirs[0]))
            cmake.definitions['LIBVLC_BIN_DIR:PATH']     = adjustPath(os.path.join(self.deps_cpp_info['vlc'].rootpath, self.deps_cpp_info['vlc'].bindirs[0]))

        if 'Windows' == self.settings.os and 'Visual Studio' == self.settings.compiler:
            # The creator of VLC Qt seems to prefer nmake, and in fact doesn't
            # support stuff build with regular VS (see
            # https://github.com/vlc-qt/vlc-qt/issues/193 )
            self.output.info('Using NMake Generator')
            cmake.generator='NMake Makefiles'

        s = '\nCMake Definitions:\n'
        for k,v in cmake.definitions.items():
            s += ' - %s=%s\n'%(k, v)
        self.output.info(s)

        return cmake, env

    def build(self):
        cmake, env = self._set_up_cmake()

        if len(env.keys()):
            s = '\nAdditional Environment:\n'
            for k,v in env.items():
                s += ' - %s=%s\n'%(k, v)
            self.output.info(s)

        with tools.environment_append(env):
            if 'Windows' == self.settings.os and 'Visual Studio' == self.settings.compiler:
                with tools.vcvars(self.settings, filter_known_paths=False):
                    cmake.configure(source_folder=self.name)
                    cmake.build()
            else:
                cmake.configure(source_folder=self.name)
                cmake.build()

    def package(self):
        cmake, env = self._set_up_cmake()
        if 'Windows' == self.settings.os and 'Visual Studio' == self.settings.compiler:
            with tools.vcvars(self.settings, filter_known_paths=False):
                cmake.install()
        else:
            cmake.install()

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)

# vim: ts=4 sw=4 expandtab ffs=unix ft=python foldmethod=marker :
