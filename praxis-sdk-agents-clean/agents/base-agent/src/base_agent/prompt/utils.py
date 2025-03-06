from jinja2 import Environment, PackageLoader


def get_environment(package_name: str, template_dir: str):
    return Environment(loader=PackageLoader(package_name=package_name,package_path=template_dir))
