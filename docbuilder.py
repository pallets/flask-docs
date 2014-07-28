import os
import json
import shutil
import tempfile
import subprocess

import click


HERE = os.path.abspath(os.path.dirname(__file__))

config_override_template = '''\
import os
import sys

sys.path.insert(0, %(theme_path)r)
#__import__('pocoo_theme_support')
sys.path[:] = [os.path.abspath(x) for x in sys.path]

# Source the old file and ensure the paths are setup correctly afterwards
_old_file = __file__
__file__ = 'conf.py'
_here = os.getcwd()
_real_path = %(real_path)r
os.chdir(_real_path)
execfile('conf.py')
sys.path[:] = [os.path.abspath(x) for x in sys.path]
os.chdir(_here)
html_static_path = [os.path.join(_real_path, _x) for _x in html_static_path]
__file__ = _old_file

# Overrides
html_favicon = None
project = %(project)r
version = %(version)r

templates_path = []
html_title = '%%s Documentation (%%s)' %% (project, version)
html_theme = %(theme)r
html_theme_options = {}
html_theme_path = [%(theme_path)r]
html_sidebars = %(sidebars)r
html_context = %(context_vars)r

pygments_style = %(pygments_style)r
'''


def build_context_vars(this_version, config):
    versions = []
    warning = None

    for version in config['versions']:
        is_current = this_version == version['slug']
        versions.append({
            'slug': version['slug'],
            'title': version['title'],
            'note': version.get('note'),
            'is_current': is_current,
        })
        if is_current:
            warning = version.get('warning')

    return {
        'documentation_versions': versions,
        'documentation_version_warning': warning,
    }


def ensure_checkout(checkout_folder, repo_url):
    try:
        os.makedirs(checkout_folder)
    except OSError:
        pass

    url, branch = repo_url.rsplit('@', 1)
    if os.path.isdir(os.path.join(checkout_folder, '.git')):
        subprocess.Popen([
            'git', 'fetch', 'origin',
            '%s:%s' % (branch, branch),
            '--update-head-ok',
            '--depth', '1',
        ], cwd=checkout_folder).wait()
        subprocess.Popen([
            'git', 'reset', '--hard',
        ], cwd=checkout_folder).wait()
        subprocess.Popen([
            'git', 'checkout', branch,
        ], cwd=checkout_folder).wait()
    else:
        subprocess.Popen([
            'git', 'clone',
            '--depth', '1',
            '--branch', branch,
            url,
            checkout_folder
        ]).wait()


def build_version(config, version_config, output_folder, checkout_folder):
    version_checkout_folder = os.path.join(
        checkout_folder, str('%s-%s' % (config['id'],
                                        version_config['slug'])))

    ensure_checkout(version_checkout_folder, version_config['repo'])
    doc_source_path = os.path.join(version_checkout_folder,
                                   str(config['doc_path']))

    config_path = tempfile.mkdtemp(prefix='.versionoverlay',
                                   dir=HERE)
    context_vars = build_context_vars(version_config['slug'], config)

    try:
        with open(os.path.join(config_path, 'conf.py'), 'w') as f:
            f.write(config_override_template % {
                'project': config['name'],
                'version': '.'.join(version_config['version'].split('.')[:2]),
                'release': version_config['version'],
                'real_path': os.path.abspath(doc_source_path),
                'theme_path': os.path.join(HERE, 'themes'),
                'theme': config.get('theme') or 'pocoo',
                'pygments_style': config.get('pygments_style')
                    or 'pocoo_theme_support.PocooStyle',
                'sidebars': config.get('sidebars') or {},
                'context_vars': context_vars,
            } + '\n')

        # Make sure the checkout is added to the pythonpath before Sphinx
        # invokes as Sphinx itself depends on Jinja2 for instance.
        env = dict(os.environ)
        env['PYTHONPATH'] = os.path.abspath(version_checkout_folder)

        for builder in'dirhtml', 'json':
            subprocess.Popen([
                'sphinx-build',
                '-d', os.path.join(doc_source_path, '.doctrees'),
                '-b', builder,
                '-c', config_path,
                '.',
                os.path.abspath(output_folder),
            ], cwd=doc_source_path, env=env).wait()
    finally:
        try:
            shutil.rmtree(config_path)
        except (OSError, IOError):
            pass


@click.group()
def cli():
    """A wrapper around sphinx-build."""


@cli.command()
@click.option('--config', type=click.Path(), required=True,
              help='The path to the documentation config file.')
@click.option('--checkout-folder', type=click.Path(),
              default='checkouts')
@click.option('--output', '-O', type=click.Path(), default=None,
              help='The path to the output folder.')
def build(config, checkout_folder, output):
    """Builds all documentation."""
    with open(config) as f:
        cfg = json.load(f)

    if output is None:
        output = 'build/%s' % str(cfg['id'])

    for version_cfg in cfg['versions']:
        build_version(cfg, version_cfg,
                      os.path.join(output, str(version_cfg['slug'])),
                      checkout_folder)
