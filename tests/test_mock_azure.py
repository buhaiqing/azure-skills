"""Tests for scripts/mock_azure.py — MockAzure class."""

from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "scripts")
from mock_azure import MockAzure  # noqa: E402


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def mock() -> MockAzure:
    return MockAzure(seed=42)


# ------------------------------------------------------------------
# 1. Module importable
# ------------------------------------------------------------------


def test_mock_azure_importable() -> None:
    """mock_azure module can be imported."""
    import importlib

    mod = importlib.import_module("mock_azure")
    assert hasattr(mod, "MockAzure")


# ------------------------------------------------------------------
# 2. vm create
# ------------------------------------------------------------------


def test_vm_create(mock: MockAzure) -> None:
    """execute vm create returns a successful result with VM details."""
    result = mock.execute(
        "az vm create --name test-vm --resource-group test-rg --image UbuntuLTS"
    )
    assert result["exit_code"] == 0
    assert result["error"] is None
    vm = result["result"]
    assert vm["name"] == "test-vm"
    assert vm["resourceGroup"] == "test-rg"
    assert vm["properties"]["provisioningState"] == "Succeeded"
    assert vm["properties"]["powerState"] == "VM running"
    assert vm["id"].startswith("/subscriptions/")
    assert "Microsoft.Compute/virtualMachines" in vm["type"]


# ------------------------------------------------------------------
# 3. vm show
# ------------------------------------------------------------------


def test_vm_show(mock: MockAzure) -> None:
    """execute vm show returns the correct resource."""
    mock.execute(
        "az vm create --name test-vm --resource-group test-rg --image UbuntuLTS"
    )
    result = mock.execute("az vm show --name test-vm --resource-group test-rg")
    assert result["exit_code"] == 0
    vm = result["result"]
    assert vm["name"] == "test-vm"
    assert vm["resourceGroup"] == "test-rg"


# ------------------------------------------------------------------
# 4. vm list
# ------------------------------------------------------------------


def test_vm_list(mock: MockAzure) -> None:
    """execute vm list returns all resources in the resource group."""
    mock.execute("az vm create --name vm1 --resource-group test-rg")
    mock.execute("az vm create --name vm2 --resource-group test-rg")
    result = mock.execute("az vm list --resource-group test-rg")
    assert result["exit_code"] == 0
    vms = result["result"]
    assert len(vms) == 2
    names = {v["name"] for v in vms}
    assert names == {"vm1", "vm2"}


# ------------------------------------------------------------------
# 5. vm delete
# ------------------------------------------------------------------


def test_vm_delete(mock: MockAzure) -> None:
    """execute vm delete marks the resource as deleted."""
    mock.execute("az vm create --name test-vm --resource-group test-rg")
    result = mock.execute(
        "az vm delete --name test-vm --resource-group test-rg --yes"
    )
    assert result["exit_code"] == 0
    assert result["result"]["status"] == "Succeeded"

    # After deletion, show should return an error
    result = mock.execute("az vm show --name test-vm --resource-group test-rg")
    assert result["exit_code"] == 1
    assert result["error"] is not None


# ------------------------------------------------------------------
# 6. Unknown command returns error
# ------------------------------------------------------------------


def test_unknown_command(mock: MockAzure) -> None:
    """execute with an unknown command returns exit_code=1 and an error."""
    result = mock.execute("az nonexistent --foo bar")
    assert result["exit_code"] == 1
    assert result["error"] is not None
    assert result["result"] is None


# ------------------------------------------------------------------
# 7. simulate_failure causes random failures
# ------------------------------------------------------------------


def test_simulate_failure(mock: MockAzure) -> None:
    """simulate_failure causes some calls to fail randomly."""
    mock.simulate_failure("vm", probability=1.0)
    result = mock.execute(
        "az vm create --name fail-vm --resource-group fail-rg"
    )
    assert result["exit_code"] == 1
    assert "simulated failure" in (result["error"] or "")


# ------------------------------------------------------------------
# 8. aks show
# ------------------------------------------------------------------


def test_aks_show(mock: MockAzure) -> None:
    """execute aks show returns cluster information."""
    mock.execute(
        "az aks create --name test-cluster --resource-group test-rg"
    )
    result = mock.execute("az aks show --name test-cluster --resource-group test-rg")
    assert result["exit_code"] == 0
    cluster = result["result"]
    assert cluster["name"] == "test-cluster"
    assert cluster["resourceGroup"] == "test-rg"
    assert cluster["type"] == "Microsoft.ContainerService/ManagedClusters"
    assert cluster["properties"]["provisioningState"] == "Succeeded"


# ------------------------------------------------------------------
# 9. storage account show
# ------------------------------------------------------------------


def test_storage_account_show(mock: MockAzure) -> None:
    """execute storage account show returns account information."""
    # Storage accounts are not created via the mock, so show will fail
    # unless we seed the resource directly.
    # We seed via the internal resource store.
    mock._put(
        "test-rg",
        "teststorage",
        {
            "id": "/subscriptions/.../storageAccounts/teststorage",
            "name": "teststorage",
            "resourceGroup": "test-rg",
            "location": "eastus",
            "sku": {"name": "Standard_LRS"},
            "kind": "StorageV2",
            "properties": {"provisioningState": "Succeeded"},
        },
    )
    result = mock.execute(
        "az storage account show --name teststorage --resource-group test-rg"
    )
    assert result["exit_code"] == 0
    account = result["result"]
    assert account["name"] == "teststorage"
    assert account["resourceGroup"] == "test-rg"


# ------------------------------------------------------------------
# 10. reset clears all state
# ------------------------------------------------------------------


def test_reset(mock: MockAzure) -> None:
    """reset clears all resources and failure probabilities."""
    mock.execute("az vm create --name vm1 --resource-group rg1")
    mock.simulate_failure("vm", probability=1.0)

    mock.reset()

    # After reset, vm1 should not exist
    result = mock.execute("az vm show --name vm1 --resource-group rg1")
    assert result["exit_code"] == 1

    # Create should work again
    result = mock.execute("az vm create --name new-vm --resource-group new-rg")
    assert result["exit_code"] == 0


# ------------------------------------------------------------------
# Additional tests for coverage of other command groups
# ------------------------------------------------------------------


def test_vm_start_stop_restart(mock: MockAzure) -> None:
    """vm start/stop/restart change power state."""
    mock.execute("az vm create --name test-vm --resource-group test-rg")

    result = mock.execute("az vm stop --name test-vm --resource-group test-rg")
    assert result["result"]["powerState"] == "VM stopped"

    result = mock.execute("az vm start --name test-vm --resource-group test-rg")
    assert result["result"]["powerState"] == "VM running"

    result = mock.execute("az vm restart --name test-vm --resource-group test-rg")
    assert result["result"]["powerState"] == "VM running"


def test_vm_get_instance_view(mock: MockAzure) -> None:
    """vm get-instance-view returns status information."""
    mock.execute("az vm create --name test-vm --resource-group test-rg")
    result = mock.execute(
        "az vm get-instance-view --name test-vm --resource-group test-rg"
    )
    assert result["exit_code"] == 0
    statuses = result["result"]["statuses"]
    assert any(s["code"] == "PowerState/running" for s in statuses)


def test_vm_list_sizes(mock: MockAzure) -> None:
    """vm list-sizes returns available VM sizes."""
    result = mock.execute("az vm list-sizes --resource-group test-rg")
    assert result["exit_code"] == 0
    sizes = result["result"]
    assert len(sizes) >= 2
    assert sizes[0]["name"] == "Standard_DS1_v2"


def test_aks_list(mock: MockAzure) -> None:
    """aks list returns all clusters."""
    mock.execute("az aks create --name cluster1 --resource-group rg1")
    mock.execute("az aks create --name cluster2 --resource-group rg1")
    result = mock.execute("az aks list --resource-group rg1")
    assert len(result["result"]) == 2


def test_aks_get_credentials(mock: MockAzure) -> None:
    """aks get-credentials returns a kubeconfig."""
    mock.execute("az aks create --name test-cluster --resource-group test-rg")
    result = mock.execute(
        "az aks get-credentials --name test-cluster --resource-group test-rg"
    )
    assert result["exit_code"] == 0
    assert "kubeconfig" in result["result"]


def test_aks_nodepool_list(mock: MockAzure) -> None:
    """aks nodepool list returns node pools."""
    mock.execute("az aks create --name test-cluster --resource-group test-rg")
    result = mock.execute(
        "az aks nodepool list --cluster-name test-cluster --resource-group test-rg"
    )
    assert result["exit_code"] == 0
    assert len(result["result"]) >= 1


def test_aks_nodepool_show(mock: MockAzure) -> None:
    """aks nodepool show returns a specific node pool."""
    mock.execute("az aks create --name test-cluster --resource-group test-rg")
    result = mock.execute(
        "az aks nodepool show --cluster-name test-cluster --resource-group test-rg --name nodepool1"
    )
    assert result["exit_code"] == 0
    assert result["result"]["name"] == "nodepool1"


def test_aks_nodepool_upgrade(mock: MockAzure) -> None:
    """aks nodepool upgrade returns upgraded pool info."""
    mock.execute("az aks create --name test-cluster --resource-group test-rg")
    result = mock.execute(
        "az aks nodepool upgrade --cluster-name test-cluster --resource-group test-rg --name nodepool1 --kubernetes-version 1.28.0"
    )
    assert result["result"]["orchestratorVersion"] == "1.28.0"


def test_aks_delete(mock: MockAzure) -> None:
    """aks delete requires --yes flag."""
    mock.execute("az aks create --name test-cluster --resource-group test-rg")

    # Without --yes should fail
    result = mock.execute("az aks delete --name test-cluster --resource-group test-rg")
    assert result["exit_code"] == 1

    # With --yes should succeed
    result = mock.execute(
        "az aks delete --name test-cluster --resource-group test-rg --yes"
    )
    assert result["exit_code"] == 0


def test_storage_account_list(mock: MockAzure) -> None:
    """storage account list returns all accounts."""
    mock._put(
        "rg1",
        "sa1",
        {"name": "sa1", "resourceGroup": "rg1", "location": "eastus"},
    )
    mock._put(
        "rg1",
        "sa2",
        {"name": "sa2", "resourceGroup": "rg1", "location": "westus"},
    )
    result = mock.execute("az storage account list --resource-group rg1")
    assert len(result["result"]) == 2


def test_storage_container_list(mock: MockAzure) -> None:
    """storage container list returns containers."""
    result = mock.execute(
        "az storage container list --account-name testaccount"
    )
    assert result["exit_code"] == 0
    assert len(result["result"]) >= 1


def test_storage_container_create(mock: MockAzure) -> None:
    """storage container create returns created container."""
    result = mock.execute(
        "az storage container create --name new-container --account-name testaccount"
    )
    assert result["result"]["created"] is True


def test_storage_blob_list(mock: MockAzure) -> None:
    """storage blob list returns blobs."""
    result = mock.execute(
        "az storage blob list --container-name mycontainer --account-name testaccount"
    )
    assert result["exit_code"] == 0
    assert len(result["result"]) >= 1


def test_storage_blob_upload(mock: MockAzure) -> None:
    """storage blob upload returns uploaded blob."""
    result = mock.execute(
        "az storage blob upload --container-name mycontainer --name myfile.txt --file /tmp/test.txt --account-name testaccount"
    )
    assert result["result"]["uploaded"] is True


def test_storage_blob_delete(mock: MockAzure) -> None:
    """storage blob delete returns deleted confirmation."""
    result = mock.execute(
        "az storage blob delete --container-name mycontainer --name myfile.txt --account-name testaccount"
    )
    assert result["result"]["deleted"] is True


def test_appgateway_show(mock: MockAzure) -> None:
    """application-gateway show returns gateway info."""
    mock._put(
        "rg1",
        "gw1",
        {
            "name": "gw1",
            "resourceGroup": "rg1",
            "location": "eastus",
            "properties": {"provisioningState": "Succeeded", "operationalState": "Running"},
        },
    )
    result = mock.execute(
        "az network application-gateway show --name gw1 --resource-group rg1"
    )
    assert result["result"]["name"] == "gw1"


def test_appgateway_start_stop(mock: MockAzure) -> None:
    """application-gateway start/stop changes operational state."""
    mock._put(
        "rg1",
        "gw1",
        {
            "name": "gw1",
            "resourceGroup": "rg1",
            "location": "eastus",
            "properties": {"provisioningState": "Succeeded", "operationalState": "Running"},
        },
    )

    result = mock.execute(
        "az network application-gateway stop --name gw1 --resource-group rg1"
    )
    assert result["result"]["status"] == "Succeeded"

    result = mock.execute(
        "az network application-gateway start --name gw1 --resource-group rg1"
    )
    assert result["result"]["status"] == "Succeeded"


def test_appgateway_delete(mock: MockAzure) -> None:
    """application-gateway delete requires --yes."""
    mock._put(
        "rg1",
        "gw1",
        {"name": "gw1", "resourceGroup": "rg1"},
    )
    result = mock.execute(
        "az network application-gateway delete --name gw1 --resource-group rg1 --yes"
    )
    assert result["result"]["status"] == "Succeeded"


def test_appgateway_probe_show(mock: MockAzure) -> None:
    """application-gateway probe show returns probe details."""
    mock._put(
        "rg1",
        "gw1",
        {"name": "gw1", "resourceGroup": "rg1"},
    )
    result = mock.execute(
        "az network application-gateway probe show --gateway-name gw1 --resource-group rg1 --name healthProbe"
    )
    assert result["result"]["protocol"] == "Http"


def test_lb_show(mock: MockAzure) -> None:
    """lb show returns load balancer info."""
    mock._put(
        "rg1",
        "lb1",
        {
            "name": "lb1",
            "resourceGroup": "rg1",
            "location": "eastus",
            "properties": {"provisioningState": "Succeeded"},
        },
    )
    result = mock.execute("az network lb show --name lb1 --resource-group rg1")
    assert result["result"]["name"] == "lb1"


def test_lb_rule_list(mock: MockAzure) -> None:
    """lb rule list returns rules."""
    mock._put(
        "rg1",
        "lb1",
        {"name": "lb1", "resourceGroup": "rg1"},
    )
    result = mock.execute(
        "az network lb rule list --lb-name lb1 --resource-group rg1"
    )
    assert len(result["result"]) >= 1


def test_lb_probe_list(mock: MockAzure) -> None:
    """lb probe list returns probes."""
    mock._put(
        "rg1",
        "lb1",
        {"name": "lb1", "resourceGroup": "rg1"},
    )
    result = mock.execute(
        "az network lb probe list --lb-name lb1 --resource-group rg1"
    )
    assert len(result["result"]) >= 1


def test_lb_delete(mock: MockAzure) -> None:
    """lb delete requires --yes."""
    mock._put(
        "rg1",
        "lb1",
        {"name": "lb1", "resourceGroup": "rg1"},
    )
    result = mock.execute(
        "az network lb delete --name lb1 --resource-group rg1 --yes"
    )
    assert result["result"]["status"] == "Succeeded"


def test_afd_profile_show(mock: MockAzure) -> None:
    """afd profile show returns profile info."""
    mock._put(
        "rg1",
        "profile1",
        {"name": "profile1", "resourceGroup": "rg1", "properties": {"provisioningState": "Succeeded"}},
    )
    result = mock.execute(
        "az afd profile show --profile-name profile1 --resource-group rg1"
    )
    assert result["result"]["name"] == "profile1"


def test_afd_endpoint_show(mock: MockAzure) -> None:
    """afd endpoint show returns endpoint info."""
    mock._put(
        "rg1",
        "profile1",
        {"name": "profile1", "resourceGroup": "rg1"},
    )
    result = mock.execute(
        "az afd endpoint show --profile-name profile1 --endpoint-name myendpoint --resource-group rg1"
    )
    assert result["result"]["name"] == "myendpoint"


def test_afd_endpoint_purge(mock: MockAzure) -> None:
    """afd endpoint purge purges content paths."""
    mock._put(
        "rg1",
        "profile1",
        {"name": "profile1", "resourceGroup": "rg1"},
    )
    result = mock.execute(
        "az afd endpoint purge --profile-name profile1 --endpoint-name myendpoint --resource-group rg1 --content-paths /images/*"
    )
    assert result["result"]["purged"] is True


def test_afd_profile_delete(mock: MockAzure) -> None:
    """afd profile delete requires --yes."""
    mock._put(
        "rg1",
        "profile1",
        {"name": "profile1", "resourceGroup": "rg1"},
    )
    result = mock.execute(
        "az afd profile delete --profile-name profile1 --resource-group rg1 --yes"
    )
    assert result["result"]["status"] == "Succeeded"


def test_vnet_show(mock: MockAzure) -> None:
    """vnet show returns VNet info."""
    mock._put(
        "rg1",
        "vnet1",
        {
            "name": "vnet1",
            "resourceGroup": "rg1",
            "location": "eastus",
            "properties": {"provisioningState": "Succeeded", "addressSpace": {"addressPrefixes": ["10.0.0.0/16"]}},
        },
    )
    result = mock.execute("az network vnet show --name vnet1 --resource-group rg1")
    assert result["result"]["name"] == "vnet1"


def test_vnet_subnet_list(mock: MockAzure) -> None:
    """vnet subnet list returns subnets."""
    mock._put(
        "rg1",
        "vnet1",
        {"name": "vnet1", "resourceGroup": "rg1"},
    )
    result = mock.execute(
        "az network vnet subnet list --vnet-name vnet1 --resource-group rg1"
    )
    assert len(result["result"]) >= 1


def test_vnet_check_ip_address(mock: MockAzure) -> None:
    """vnet check-ip-address returns availability."""
    mock._put(
        "rg1",
        "vnet1",
        {"name": "vnet1", "resourceGroup": "rg1"},
    )
    result = mock.execute(
        "az network vnet check-ip-address --name vnet1 --resource-group rg1 --ip-address 10.0.0.1"
    )
    assert result["result"]["available"] is True

    result = mock.execute(
        "az network vnet check-ip-address --name vnet1 --resource-group rg1 --ip-address 10.0.0.5"
    )
    assert result["result"]["available"] is False


def test_vnet_peering_list(mock: MockAzure) -> None:
    """vnet peering list returns peerings."""
    mock._put(
        "rg1",
        "vnet1",
        {"name": "vnet1", "resourceGroup": "rg1"},
    )
    result = mock.execute(
        "az network vnet peering list --vnet-name vnet1 --resource-group rg1"
    )
    assert len(result["result"]) >= 1


def test_keyvault_show(mock: MockAzure) -> None:
    """keyvault show returns vault info."""
    mock._put(
        "rg1",
        "kv1",
        {"name": "kv1", "resourceGroup": "rg1", "properties": {"provisioningState": "Succeeded"}},
    )
    result = mock.execute("az keyvault show --name kv1 --resource-group rg1")
    assert result["result"]["name"] == "kv1"


def test_keyvault_secret_list(mock: MockAzure) -> None:
    """keyvault secret list returns secrets."""
    mock._put(
        "rg1",
        "kv1",
        {"name": "kv1", "resourceGroup": "rg1"},
    )
    result = mock.execute("az keyvault secret list --vault-name kv1")
    assert len(result["result"]) >= 1


def test_keyvault_secret_show(mock: MockAzure) -> None:
    """keyvault secret show returns secret details."""
    mock._put(
        "rg1",
        "kv1",
        {"name": "kv1", "resourceGroup": "rg1"},
    )
    result = mock.execute(
        "az keyvault secret show --vault-name kv1 --name mysecret"
    )
    assert result["result"]["name"] == "mysecret"
    assert "***mocked-secret-value***" in result["result"]["value"]


def test_keyvault_key_list(mock: MockAzure) -> None:
    """keyvault key list returns keys."""
    mock._put(
        "rg1",
        "kv1",
        {"name": "kv1", "resourceGroup": "rg1"},
    )
    result = mock.execute("az keyvault key list --vault-name kv1")
    assert len(result["result"]) >= 1


def test_vm_delete_without_yes(mock: MockAzure) -> None:
    """vm delete without --yes flag returns an error."""
    mock.execute("az vm create --name test-vm --resource-group test-rg")
    result = mock.execute("az vm delete --name test-vm --resource-group test-rg")
    assert result["exit_code"] == 1
    assert "--yes" in (result["error"] or "")


def test_vm_deallocate(mock: MockAzure) -> None:
    """vm deallocate changes power state to deallocated."""
    mock.execute("az vm create --name test-vm --resource-group test-rg")
    result = mock.execute(
        "az vm deallocate --name test-vm --resource-group test-rg"
    )
    assert result["result"]["powerState"] == "VM deallocated"


def test_not_az_command(mock: MockAzure) -> None:
    """Commands that don't start with 'az' return an error."""
    result = mock.execute("not-an-az-command")
    assert result["exit_code"] == 1
    assert "not an az command" in (result["error"] or "")
