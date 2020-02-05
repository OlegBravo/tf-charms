import os
from subprocess import check_call

from charmhelpers.core.hookenv import status_set
from charmhelpers.core.hookenv import config
from charmhelpers.core.host import service_restart
from charmhelpers.core.templating import render

from charms.reactive import remove_state
from charms.reactive import set_state
from charms.reactive import when
from charms.reactive import when_not

from charms.docker import DockerOpts

from charms import layer

# 2 Major events are emitted from this layer.
#
# `docker.ready` is an event intended to signal other layers that need to
# plug into the plumbing to extend the docker daemon. Such as fire up a
# bootstrap docker daemon, or predependency fetch + dockeropt rendering
#
# `docker.available` means the docker daemon setup has settled and is prepared
# to run workloads. This is a broad state that has large implications should
# you decide to remove it. Production workloads can be lost if no restart flag
# is provided.

# Be sure you bind to it appropriately in your workload layer and
# react to the proper event.


@when_not('docker.ready')
def install():
    ''' Install the docker daemon, and supporting tooling '''

    # Often when building layer-docker based subordinates, you dont need to
    # incur the overhead of installing docker. This tuneable layer option
    # allows you to disable the exec of that install routine, and instead short
    # circuit immediately to docker.available, so you can charm away!
    layer_opts = layer.options('docker')
    if layer_opts['skip-install']:
        set_state('docker.available')
        set_state('docker.ready')
        return

    status_set('maintenance', 'Installing Docker and AUFS')
    # Using getenv will return '' if CHARM_DIR is not an environment variable.
    charm_path = os.getenv('CHARM_DIR', '')
    install_script_path = os.path.join(charm_path, 'scripts/install_docker.sh')
    check_call([install_script_path])
    status_set('active', 'Docker installed, cycling for extensions')
    set_state('docker.ready')

    # Make with the adding of the users to the groups
    check_call(['usermod', '-aG', 'docker', 'ubuntu'])


@when('docker.ready')
@when_not('cgroups.modified')
def enable_grub_cgroups():
    cfg = config()
    if cfg.get('enable-cgroups'):
        check_call(['scripts/enable_grub_cgroups.sh'])
        set_state('cgroups.modified')


@when('docker.ready')
@when_not('docker.available')
def signal_workloads_start():
    ''' We can assume the pre-workload bits have completed now that docker.ready
    has been reacted to. Lets remove the predep work and continue on to being
    available '''
    status_set('active', 'Docker installed')
    set_state('docker.available')


@when('docker.restart')
def recycle_daemon():
    ''' Other layers should be able to trigger a daemon restart '''
    status_set('maintenance', 'Restarting docker daemon')

    # Re-render our docker daemon template at this time... because we're
    # restarting. And its nice to play nice with others. Isn't that nice?
    opts = DockerOpts()
    render('docker.defaults', '/etc/default/docker', {'opts': opts.to_s()})

    service_restart('docker')
    remove_state('docker.restart')
