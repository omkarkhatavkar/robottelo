"""Test class for Virtwho Configure UI

:Requirement: Virt-whoConfigurePlugin

:CaseAutomation: Automated

:CaseLevel: Acceptance

:CaseComponent: Virt-whoConfigurePlugin

:TestType: Functional

:CaseImportance: High

:Upstream: No
"""
from fauxfactory import gen_string

from robottelo.config import settings
from robottelo.decorators import fixture
from robottelo.decorators import tier2
from robottelo.virtwho_utils import deploy_configure_by_command
from robottelo.virtwho_utils import deploy_configure_by_script


@fixture()
def form_data():
    form = {
        'debug': True,
        'interval': 'Every hour',
        'hypervisor_id': 'hostname',
        'hypervisor_type': settings.virtwho.hypervisor_type,
        'hypervisor_content.kubeconfig': settings.virtwho.hypervisor_config_file,
    }
    return form


class TestVirtwhoConfigforKubevirt:
    @tier2
    def test_positive_deploy_configure_by_id(self, session, form_data):
        """ Verify configure created and deployed with id.

        :id: 7b2a1b08-f33c-44f4-ad2e-317b6c44b938

        :expectedresults:
            1. Config can be created and deployed by command
            2. No error msg in /var/log/rhsm/rhsm.log
            3. Report is sent to satellite
            4. Virtual sku can be generated and attached
            5. Config can be deleted

        :CaseLevel: Integration

        :CaseImportance: High
        """
        name = gen_string('alpha')
        form_data['name'] = name
        with session:
            session.virtwho_configure.create(form_data)
            values = session.virtwho_configure.read(name)
            command = values['deploy']['command']
            hypervisor_name, guest_name = deploy_configure_by_command(command, debug=True)
            assert session.virtwho_configure.search(name)[0]['Status'] == 'ok'
            hypervisor_display_name = session.contenthost.search(hypervisor_name)[0]['Name']
            vdc_physical = 'product_id = {} and type=NORMAL'.format(
                settings.virtwho.sku_vdc_physical
            )
            vdc_virtual = 'product_id = {} and type=STACK_DERIVED'.format(
                settings.virtwho.sku_vdc_physical
            )
            session.contenthost.add_subscription(hypervisor_display_name, vdc_physical)
            assert session.contenthost.search(hypervisor_name)[0]['Subscription Status'] == 'green'
            session.contenthost.add_subscription(guest_name, vdc_virtual)
            assert session.contenthost.search(guest_name)[0]['Subscription Status'] == 'green'
            session.virtwho_configure.delete(name)
            assert not session.virtwho_configure.search(name)

    @tier2
    def test_positive_deploy_configure_by_script(self, session, form_data):
        """ Verify configure created and deployed with script.

        :id: b3903ccb-04cc-4867-b7ed-d5053d2bfe03

        :expectedresults:
            1. Config can be created and deployed by script
            2. No error msg in /var/log/rhsm/rhsm.log
            3. Report is sent to satellite
            4. Virtual sku can be generated and attached
            5. Config can be deleted

        :CaseLevel: Integration

        :CaseImportance: High
        """
        name = gen_string('alpha')
        form_data['name'] = name
        with session:
            session.virtwho_configure.create(form_data)
            values = session.virtwho_configure.read(name)
            script = values['deploy']['script']
            hypervisor_name, guest_name = deploy_configure_by_script(script, debug=True)
            assert session.virtwho_configure.search(name)[0]['Status'] == 'ok'
            hypervisor_display_name = session.contenthost.search(hypervisor_name)[0]['Name']
            vdc_physical = 'product_id = {} and type=NORMAL'.format(
                settings.virtwho.sku_vdc_physical
            )
            vdc_virtual = 'product_id = {} and type=STACK_DERIVED'.format(
                settings.virtwho.sku_vdc_physical
            )
            session.contenthost.add_subscription(hypervisor_display_name, vdc_physical)
            assert session.contenthost.search(hypervisor_name)[0]['Subscription Status'] == 'green'
            session.contenthost.add_subscription(guest_name, vdc_virtual)
            assert session.contenthost.search(guest_name)[0]['Subscription Status'] == 'green'
            session.virtwho_configure.delete(name)
            assert not session.virtwho_configure.search(name)
