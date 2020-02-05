from subprocess import check_call

from charms.reactive import when_not
from charms.reactive import set_state

from charmhelpers.core import hookenv


@when_not('cgroups.modified')
def enable_grub_cgroups():
    """
    Run script to enable cgroups
    in GRUB.  Be aware, this will
    reboot the host.

    :return: None
    """
    cfg = hookenv.config()
    if cfg.get('enable-cgroups'):
        hookenv.log('Calling enable_grub_cgroups.sh and rebooting machine.')
        check_call(['scripts/enable_grub_cgroups.sh'])
        set_state('cgroups.modified')

