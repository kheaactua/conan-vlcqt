#!/usr/bin/env python
# -*- coding: future_fstrings -*-
# -*- coding: utf-8 -*-

import os
from conans import ConanFile, CMake, tools


class VlcqtConan(ConanFile):
    name            = 'vlcqt'
    version         = '1.1.1'
    license         = ''
    url             = 'https://github.com/kheaactua/conan-vlcqt'
    description     = 'Build VLC Qt'
    settings        = 'os', 'compiler', 'build_type', 'arch'
    options         = {'shared': [True, False]}
    default_options = 'shared= False'
    generators      = 'cmake'

    requires        = (
        'helpers/[>=0.3]@ntc/stable',
        'qt/[>=5.9.0]@ntc/stable',
    )

    def source(self):
        self.run('git clone https://github.com/vlc-qt/vlc-qt.git .')
        self.run('git checkout %s'%self.version)

    def build(self):
        # Import from helpers/x@ntc/stable
        from platform_helpers import adjustPath

        cmake = CMake(self)

        cmake.definitions['STATIC'] = 'FALSE' if self.options.shared else 'TRUE'

        qt_deps = ['Core']
        for p in qt_deps:
            cmake.definitions[f'Qt5{p}_DIR:PATH'] = adjustPath(os.path.join(self.deps_cpp_info['qt'].rootpath, 'lib', 'cmake', f'Qt5{p}'))
        cmake.definitions['QT_QMAKE_EXECUTABLE:PATH'] = adjustPath(os.path.join(self.deps_cpp_info['qt'].rootpath, 'bin', 'qmake'))

        # # if windows, specify
        # cmake.definitions['LIBVLC_LIBRARY:PATH'] = 
        # cmake.definitions['LIBVLCCORE_LIBRARY:PATH'] = 
        # cmake.definitions['LIBVLC_INCLUDE_DIR:PATH'] = 
        # cmake.definitions['LIBVLC_BIN_DIR:PATH'] = 

        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)

# vim: ts=4 sw=4 expandtab ffs=unix ft=python foldmethod=marker :
