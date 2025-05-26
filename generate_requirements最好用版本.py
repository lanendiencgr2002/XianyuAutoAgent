#!/usr/bin/env python
import subprocess
import sys
import os
import tempfile
import json
from typing import Dict, Set, List, Tuple
from pathlib import Path
import argparse
def get_imported_packages(project_path: str) -> set:
    """使用pipreqs扫描项目中实际导入的包"""
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        # 使用pipreqs扫描项目
        result = subprocess.run([sys.executable, '-m', 'pipreqs.pipreqs', project_path, '--force', '--savepath', temp_path],
                              check=True, capture_output=True, text=True)
        
        # 读取扫描结果
        imported_packages = set()
        with open(temp_path, 'r') as f:
            for line in f:
                package = line.strip().split('==')[0].lower()
                imported_packages.add(package)
        
        return imported_packages
    except subprocess.CalledProcessError as e:
        print(f"警告: pipreqs 执行失败: {e.stderr.decode() if e.stderr else str(e)}")
        return set()
    finally:
        try:
            os.unlink(temp_path)
        except:
            pass

def get_package_version(package_name: str) -> str:
    """获取包的版本号，使用多种方法尝试"""
    try:
        # 方法1: 使用pip show
        result = subprocess.run([sys.executable, '-m', 'pip', 'show', package_name],
                              check=True, capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if line.startswith('Version: '):
                return line.split('Version: ')[1].strip()
        
        # 方法2: 使用pip freeze
        result = subprocess.run([sys.executable, '-m', 'pip', 'freeze'],
                              check=True, capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if line.lower().startswith(f"{package_name}=="):
                return line.split('==')[1].strip()
        
        # 方法3: 使用pipdeptree
        result = subprocess.run([sys.executable, '-m', 'pipdeptree', '--freeze'],
                              check=True, capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if line.lower().startswith(f"{package_name}=="):
                return line.split('==')[1].strip()
        
        # 方法4: 尝试安装最新版本
        print(f"警告: 未能找到 {package_name} 的版本信息，将使用最新版本")
        return "latest"
    except subprocess.CalledProcessError:
        return "latest"

def get_dependency_tree() -> Tuple[Dict[str, str], Dict[str, Set[str]]]:
    """使用pipdeptree获取依赖树
    返回: (包名->版本映射, 包名->子依赖集合映射)
    """
    try:
        # 获取JSON格式的依赖树
        json_cmd = [sys.executable, '-m', 'pipdeptree', '--json-tree']
        json_result = subprocess.run(json_cmd, check=True, capture_output=True, text=True)
        tree = json.loads(json_result.stdout)
        
        # 获取版本信息
        freeze_cmd = [sys.executable, '-m', 'pipdeptree', '--freeze']
        freeze_result = subprocess.run(freeze_cmd, check=True, capture_output=True, text=True)
        
        # 解析版本信息
        versions = {}
        for line in freeze_result.stdout.splitlines():
            if '==' in line:
                name, version = line.split('==')
                if not ('/' in version or '\\' in version):  # 过滤本地路径
                    versions[name.strip().lower()] = version.strip()
        
        # 构建依赖关系图
        deps_graph = {}
        
        def process_dependencies(pkg_info):
            pkg_name = pkg_info.get('key', '').lower()
            if not pkg_name:
                return
            
            deps_graph[pkg_name] = set()
            for dep in pkg_info.get('dependencies', []):
                dep_name = dep.get('key', '').lower()
                if dep_name:
                    deps_graph[pkg_name].add(dep_name)
                    # 递归处理子依赖
                    process_dependencies(dep)
        
        # 处理依赖树
        for package in tree:
            process_dependencies(package)
        
        return versions, deps_graph
    except subprocess.CalledProcessError as e:
        print(f"警告: pipdeptree 执行失败: {e.stderr.decode() if e.stderr else str(e)}")
        return {}, {}
    except json.JSONDecodeError:
        print("警告: 无法解析pipdeptree输出")
        return {}, {}
    except Exception as e:
        print(f"警告: 处理依赖时出错: {str(e)}")
        return {}, {}

def get_all_dependencies(direct_deps: set, deps_graph: Dict[str, Set[str]]) -> set:
    """获取所有必需的依赖（包括子依赖）"""
    all_deps = set(direct_deps)
    to_process = set(direct_deps)
    
    while to_process:
        dep = to_process.pop()
        if dep in deps_graph:
            new_deps = deps_graph[dep] - all_deps
            all_deps.update(new_deps)
            to_process.update(new_deps)
    
    return all_deps

def normalize_package_name(package_name: str) -> str:
    """标准化包名（处理特殊字符）"""
    # 处理带连字符的包名
    if '-' in package_name:
        return package_name.replace('-', '_')
    return package_name

def generate_requirements(project_path: str, output_file: str = 'requirements.txt', no_subdeps: bool = True):
    """生成项目依赖文件"""
    print("正在扫描项目导入的包...")
    direct_deps = get_imported_packages(project_path)
    
    if not direct_deps:
        print("错误: 未能找到任何导入的包")
        return
    
    print(f"\n找到 {len(direct_deps)} 个直接导入的包:")
    for package in sorted(direct_deps):
        print(f"  - {package}")
    
    print("\n正在分析依赖关系...")
    versions, deps_graph = get_dependency_tree()
    
    if not versions or not deps_graph:
        print("错误: 未能获取依赖信息")
        return
    
    # 获取所有必需的依赖
    all_deps = get_all_dependencies(direct_deps, deps_graph)
    subdeps = all_deps - direct_deps
    
    if subdeps and not no_subdeps:
        print(f"\n找到 {len(subdeps)} 个必要的子依赖:")
        for package in sorted(subdeps):
            print(f"  - {package}")
    
    # 生成requirements.txt
    print("\n正在生成requirements.txt...")
    with open(output_file, 'w', encoding='utf-8') as f:
        # f.write("# 直接依赖\n")
        for package in sorted(direct_deps):
            normalized_name = normalize_package_name(package)
            version = versions.get(normalized_name, '') or get_package_version(normalized_name)
            if version and version != "latest":
                f.write(f"{package}=={version}\n")
            else:
                print(f"警告: 未能找到 {package} 的版本信息")
                f.write(f"{package}\n")
        
        if subdeps and not no_subdeps:
            # f.write("\n# 子依赖\n")
            for package in sorted(subdeps):
                normalized_name = normalize_package_name(package)
                version = versions.get(normalized_name, '') or get_package_version(normalized_name)
                if version and version != "latest":
                    f.write(f"{package}=={version}\n")
                else:
                    print(f"警告: 未能找到 {package} 的版本信息")
                    f.write(f"{package}\n")
    
    print(f"\n依赖已保存到 {output_file}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='生成项目依赖文件')
    parser.add_argument('--path', default='.', help='项目路径')
    parser.add_argument('--output', default='requirements.txt', help='输出文件路径')
    
    args = parser.parse_args()
    generate_requirements(args.path, args.output) 

if __name__ == '__main__':
    # 当前目录
    nowparenpath=str(Path(__file__).parent)
    generate_requirements(nowparenpath,'requirements.txt')
