#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 加载所有测试
loader = unittest.TestLoader()
start_dir = os.path.join(os.path.dirname(__file__), 'tests')
suite = loader.discover(start_dir, pattern='test_*.py')

# 运行测试
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

# 根据测试结果设置退出码
sys.exit(not result.wasSuccessful()) 