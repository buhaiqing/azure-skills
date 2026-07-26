"""Mock Azure CLI — simulate `az` commands with zero external dependencies.

Provides a MockAzure class that parses az command strings and returns
deterministic mock JSON responses matching the real CLI output shape.
Designed for L4 auto-feedback-loop testing without a real Azure subscription.
"""

from __future__ import annotations

import copy
import hashlib
import random
import re
import shlex
from typing import Any


class MockAzure:
    """Deterministic mock for Azure CLI commands.

    Usage::

        mock = MockAzure(seed=42)
        result = mock.execute("az vm show --name my-vm --resource-group my-rg")
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)
        self._seed = seed
        self._resources: dict[str, dict[str, Any]] = {}
        self._deleted: set[tuple[str, str]] = set()
        self._counters: dict[str, int] = {}
        self._failure_probs: dict[str, float] = {}
        self._rng_for_data = random.Random(seed)  # separate RNG for data generation

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, command: str) -> dict[str, Any]:
        """Parse and execute a mock ``az`` command string.

        Returns:
            ``{"result": ..., "exit_code": 0, "error": None}`` on success, or
            ``{"result": None, "exit_code": 1, "error": "..."}`` on failure.
        """
        parts = shlex.split(command)
        if not parts or parts[0] != "az":
            return self._error(f"not an az command: {command}")

        tokens = parts[1:]  # strip "az"
        if not tokens:
            return self._error("empty az subcommand")

        # Determine service group (the first non-flag token)
        service = self._detect_service(tokens)
        if service and self._should_fail(service):
            return self._error(f"simulated failure for service: {service}")

        try:
            return self._dispatch(tokens)
        except KeyError as exc:
            return self._error(f"resource not found: {exc}")
        except ValueError as exc:
            return self._error(str(exc))
        except Exception as exc:
            return self._error(f"unexpected error: {exc}")

    def simulate_failure(self, service: str, probability: float = 0.1) -> None:
        """Set failure probability (0.0–1.0) for a specific service."""
        self._failure_probs[service] = probability

    def reset(self) -> None:
        """Reset all state — resources, deleted markers, counters, and failure probs."""
        self._resources.clear()
        self._deleted.clear()
        self._counters.clear()
        self._failure_probs.clear()
        self._rng = random.Random(self._seed)
        self._rng_for_data = random.Random(self._seed)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _error(msg: str) -> dict[str, Any]:
        return {"result": None, "exit_code": 1, "error": msg}

    @staticmethod
    def _ok(data: Any) -> dict[str, Any]:
        return {"result": data, "exit_code": 0, "error": None}

    def _next_id(self, service: str) -> str:
        self._counters.setdefault(service, 0)
        self._counters[service] += 1
        raw = f"{service}-{self._seed}-{self._counters[service]}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def _r(self) -> float:
        return self._rng.random()

    def _should_fail(self, service: str) -> bool:
        prob = self._failure_probs.get(service, 0.0)
        return prob > 0 and self._r() < prob

    @staticmethod
    def _detect_service(tokens: list[str]) -> str | None:
        """Map the first positional token(s) to a service name."""
        if not tokens:
            return None
        t = tokens[0]
        if t in ("vm", "aks", "keyvault", "afd"):
            return t
        if t == "network":
            if len(tokens) > 1 and tokens[1] in (
                "application-gateway",
                "lb",
                "vnet",
            ):
                return tokens[1]
            return None
        if t == "storage":
            return "storage"
        return None

    # ------------------------------------------------------------------
    # Argument parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_kwargs(tokens: list[str]) -> dict[str, str]:
        """Extract ``--key value`` pairs from a token list."""
        kwargs: dict[str, str] = {}
        i = 0
        while i < len(tokens):
            t = tokens[i]
            if t.startswith("--"):
                key = t.lstrip("-").replace("-", "_")
                if i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                    kwargs[key] = tokens[i + 1]
                    i += 2
                else:
                    kwargs[key] = "true"
                    i += 1
            else:
                i += 1
        return kwargs

    @staticmethod
    def _strip_flags(tokens: list[str]) -> list[str]:
        """Remove ``--key value`` pairs, leaving positional tokens."""
        result: list[str] = []
        i = 0
        while i < len(tokens):
            if tokens[i].startswith("--"):
                if i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                    i += 2
                else:
                    i += 1
            else:
                result.append(tokens[i])
                i += 1
        return result

    @staticmethod
    def _flag_present(name: str, tokens: list[str]) -> bool:
        return f"--{name}" in tokens or f"--{name.replace('_', '-')}" in tokens

    # ------------------------------------------------------------------
    # Resource helpers
    # ------------------------------------------------------------------

    def _res_key(self, rg: str, name: str) -> tuple[str, str]:
        return (rg, name)

    def _ensure_rg(self, rg: str) -> None:
        if rg not in self._resources:
            self._resources[rg] = {}

    def _put(self, rg: str, name: str, resource: dict[str, Any]) -> None:
        self._ensure_rg(rg)
        self._resources[rg][name] = resource

    def _get(self, rg: str, name: str) -> dict[str, Any]:
        rg_resources = self._resources.get(rg, {})
        res = rg_resources.get(name)
        if res is None or (rg, name) in self._deleted:
            raise KeyError(f"{name} in {rg}")
        return res

    def _delete_res(self, rg: str, name: str) -> None:
        self._deleted.add((rg, name))

    def _is_deleted(self, rg: str, name: str) -> bool:
        return (rg, name) in self._deleted

    def _list_rg(self, rg: str) -> list[dict[str, Any]]:
        rg_resources = self._resources.get(rg, {})
        return [
            v for k, v in rg_resources.items() if (rg, k) not in self._deleted
        ]

    # ------------------------------------------------------------------
    # Location helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _random_location(rng: random.Random) -> str:
        locs = [
            "eastus",
            "westus",
            "westeurope",
            "southeastasia",
            "japaneast",
        ]
        return rng.choice(locs)

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    def _dispatch(self, tokens: list[str]) -> dict[str, Any]:
        cmd = tokens[0]
        kwargs = self._parse_kwargs(tokens)

        if cmd == "vm":
            return self._dispatch_vm(tokens[1:], kwargs)
        if cmd == "aks":
            return self._dispatch_aks(tokens[1:], kwargs)
        if cmd == "network":
            return self._dispatch_network(tokens[1:], kwargs)
        if cmd == "storage":
            return self._dispatch_storage(tokens[1:], kwargs)
        if cmd == "afd":
            return self._dispatch_afd(tokens[1:], kwargs)
        if cmd == "keyvault":
            return self._dispatch_keyvault(tokens[1:], kwargs)
        return self._error(f"unknown command: az {' '.join(tokens)}")

    # ------------------------------------------------------------------
    # VM commands
    # ------------------------------------------------------------------

    def _dispatch_vm(
        self, sub: list[str], kwargs: dict[str, str]
    ) -> dict[str, Any]:
        if not sub:
            return self._error("vm subcommand required")
        action = sub[0]
        name = kwargs.get("name", "")
        rg = kwargs.get("resource_group", "")
        image = kwargs.get("image", "UbuntuLTS")

        if action == "create":
            if not name or not rg:
                return self._error("--name and --resource-group required")
            vm_id = self._next_id("vm")
            loc = self._random_location(self._rng_for_data)
            vm: dict[str, Any] = {
                "id": f"/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/{name}",
                "name": name,
                "location": loc,
                "resourceGroup": rg,
                "properties": {
                    "vmId": vm_id,
                    "hardwareProfile": {"vmSize": "Standard_DS2_v2"},
                    "storageProfile": {
                        "imageReference": {"offer": image, "publisher": "Canonical", "sku": "18.04-LTS", "version": "latest"},
                        "osDisk": {"name": f"{name}_OsDisk_1", "caching": "ReadWrite", "createOption": "FromImage", "managedDisk": {"storageAccountType": "Premium_LRS"}},
                    },
                    "osProfile": {"computerName": name, "adminUsername": "azureuser"},
                    "provisioningState": "Succeeded",
                    "powerState": "VM running",
                },
                "type": "Microsoft.Compute/virtualMachines",
            }
            self._put(rg, name, vm)
            return self._ok(vm)

        if action == "show":
            return self._ok(self._get(rg, name))

        if action in ("get-instance-view",):
            vm = self._get(rg, name)
            return self._ok(
                {
                    "name": name,
                    "resourceGroup": rg,
                    "statuses": [
                        {"code": "PowerState/running", "level": "Info", "displayStatus": "VM running", "time": "2026-07-26T00:00:00Z"},
                    ],
                    "vmAgent": {"vmAgentVersion": "2.7.1.1", "statuses": [{"code": "ProvisioningState/succeeded", "level": "Info", "displayStatus": "Ready"}]},
                }
            )

        if action == "list":
            return self._ok(self._list_rg(rg))

        if action in ("start", "stop", "restart", "deallocate"):
            vm = self._get(rg, name)
            power_map = {"start": "VM running", "stop": "VM stopped", "restart": "VM running", "deallocate": "VM deallocated"}
            status_map = {"start": "PowerState/running", "stop": "PowerState/stopped", "restart": "PowerState/running", "deallocate": "PowerState/deallocated"}
            vm["properties"]["powerState"] = power_map[action]
            return self._ok(
                {
                    "name": name,
                    "resourceGroup": rg,
                    "status": "Succeeded",
                    "powerState": power_map[action],
                }
            )

        if action == "delete":
            if not self._flag_present("yes", sub):
                return self._error("--yes flag required for delete")
            self._delete_res(rg, name)
            return self._ok(
                {"status": "Succeeded", "name": name, "resourceGroup": rg}
            )

        if action == "list-sizes":
            sizes = [
                {"name": "Standard_DS1_v2", "numberOfCores": 1, "memoryInMB": 3584, "maxDataDiskCount": 4, "osDiskSizeInMB": 1047552, "resourceDiskSizeInMB": 7168},
                {"name": "Standard_DS2_v2", "numberOfCores": 2, "memoryInMB": 7168, "maxDataDiskCount": 8, "osDiskSizeInMB": 1047552, "resourceDiskSizeInMB": 14336},
                {"name": "Standard_DS3_v2", "numberOfCores": 4, "memoryInMB": 14336, "maxDataDiskCount": 16, "osDiskSizeInMB": 1047552, "resourceDiskSizeInMB": 28672},
            ]
            return self._ok(sizes)

        return self._error(f"unknown vm subcommand: {action}")

    # ------------------------------------------------------------------
    # AKS commands
    # ------------------------------------------------------------------

    def _dispatch_aks(
        self, sub: list[str], kwargs: dict[str, str]
    ) -> dict[str, Any]:
        if not sub:
            return self._error("aks subcommand required")
        action = sub[0]
        name = kwargs.get("name", "")
        rg = kwargs.get("resource_group", "")
        cluster_name = kwargs.get("cluster_name", name)

        if action == "create":
            if not name or not rg:
                return self._error("--name and --resource-group required")
            cluster = self._create_aks_cluster(name, rg, kwargs)
            return self._ok(cluster)

        if action == "show":
            cluster = self._get(rg, name)
            return self._ok(cluster)

        if action == "list":
            return self._ok(self._list_rg(rg))

        if action == "get-credentials":
            cluster = self._get(rg, name)
            kubeconfig = (
                f"apiVersion: v1\nkind: Config\n"
                f"clusters:\n- cluster:\n    server: https://{name}-dns-{self._next_id('aks')}.hcp.eastus.azmk8s.io:443\n"
                f"  name: {name}\n"
                f"users:\n- name: clusterUser_{rg}_{name}\n  user:\n    token: mocked-token\n"
            )
            return self._ok({"kubeconfig": kubeconfig})

        if action == "nodepool":
            return self._dispatch_aks_nodepool(sub[1:], kwargs, cluster_name, rg)

        if action == "delete":
            if not self._flag_present("yes", sub):
                return self._error("--yes flag required for delete")
            self._delete_res(rg, name)
            return self._ok({"status": "Succeeded", "name": name, "resourceGroup": rg})

        return self._error(f"unknown aks subcommand: {action}")

    def _dispatch_aks_nodepool(
        self, sub: list[str], kwargs: dict[str, str], cluster: str, rg: str
    ) -> dict[str, Any]:
        if not sub:
            return self._error("nodepool subcommand required")
        action = sub[0]
        pool_name = kwargs.get("name", "nodepool1")

        if action == "list":
            pools = [
                {
                    "name": "nodepool1",
                    "count": 3,
                    "vmSize": "Standard_DS2_v2",
                    "osType": "Linux",
                    "provisioningState": "Succeeded",
                    "mode": "System",
                    "orchestratorVersion": "1.27.3",
                },
                {
                    "name": "nodepool2",
                    "count": 5,
                    "vmSize": "Standard_DS3_v2",
                    "osType": "Linux",
                    "provisioningState": "Succeeded",
                    "mode": "User",
                    "orchestratorVersion": "1.27.3",
                },
            ]
            return self._ok(pools)

        if action == "show":
            return self._ok(
                {
                    "name": pool_name,
                    "count": 3,
                    "vmSize": "Standard_DS2_v2",
                    "osType": "Linux",
                    "provisioningState": "Succeeded",
                    "mode": "System",
                    "orchestratorVersion": "1.27.3",
                }
            )

        if action == "upgrade":
            version = kwargs.get("kubernetes_version", "1.28.0")
            return self._ok(
                {
                    "name": pool_name,
                    "count": 3,
                    "vmSize": "Standard_DS2_v2",
                    "osType": "Linux",
                    "provisioningState": "Succeeded",
                    "mode": "System",
                    "orchestratorVersion": version,
                }
            )

        return self._error(f"unknown nodepool subcommand: {action}")

    def _create_aks_cluster(
        self, name: str, rg: str, kwargs: dict[str, str]
    ) -> dict[str, Any]:
        """Internal helper to create an AKS cluster resource."""
        loc = self._random_location(self._rng_for_data)
        version = kwargs.get("kubernetes_version", "1.27.3")
        cluster: dict[str, Any] = {
            "id": f"/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/{rg}/providers/Microsoft.ContainerService/managedClusters/{name}",
            "name": name,
            "location": loc,
            "resourceGroup": rg,
            "type": "Microsoft.ContainerService/ManagedClusters",
            "properties": {
                "provisioningState": "Succeeded",
                "powerState": {"code": "Running"},
                "kubernetesVersion": version,
                "dnsPrefix": f"{name}-dns",
                "fqdn": f"{name}-dns-{self._next_id('aks')}.hcp.eastus.azmk8s.io",
                "agentPoolProfiles": [
                    {
                        "name": "nodepool1",
                        "count": 3,
                        "vmSize": "Standard_DS2_v2",
                        "osType": "Linux",
                        "provisioningState": "Succeeded",
                        "mode": "System",
                    }
                ],
            },
        }
        self._put(rg, name, cluster)
        return cluster

    # ------------------------------------------------------------------
    # Storage commands
    # ------------------------------------------------------------------

    def _dispatch_storage(
        self, sub: list[str], kwargs: dict[str, str]
    ) -> dict[str, Any]:
        if not sub:
            return self._error("storage subcommand required")
        action = sub[0]
        name = kwargs.get("name", "")
        rg = kwargs.get("resource_group", "")
        account_name = kwargs.get("account_name", "")

        if action == "account":
            return self._dispatch_storage_account(sub[1:], kwargs, rg)

        if action == "container":
            return self._dispatch_storage_container(sub[1:], kwargs, account_name)

        if action == "blob":
            return self._dispatch_storage_blob(sub[1:], kwargs, account_name)

        return self._error(f"unknown storage subcommand: {action}")

    def _dispatch_storage_account(
        self, sub: list[str], kwargs: dict[str, str], rg: str
    ) -> dict[str, Any]:
        if not sub:
            return self._error("storage account subcommand required")
        action = sub[0]
        name = kwargs.get("name", "")

        if action == "create":
            if not name or not rg:
                return self._error("--name and --resource-group required")
            sku = kwargs.get("sku", "Standard_LRS")
            loc = self._random_location(self._rng_for_data)
            account: dict[str, Any] = {
                "id": f"/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{name}",
                "name": name,
                "location": loc,
                "resourceGroup": rg,
                "sku": {"name": sku},
                "kind": "StorageV2",
                "type": "Microsoft.Storage/storageAccounts",
                "properties": {"provisioningState": "Succeeded"},
            }
            self._put(rg, name, account)
            return self._ok(account)

        if action == "show":
            return self._ok(self._get(rg, name))

        if action == "list":
            return self._ok(self._list_rg(rg))

        if action == "delete":
            if not self._flag_present("yes", sub):
                return self._error("--yes flag required for delete")
            self._delete_res(rg, name)
            return self._ok({"status": "Succeeded", "name": name, "resourceGroup": rg})

        return self._error(f"unknown storage account subcommand: {action}")

    def _dispatch_storage_container(
        self, sub: list[str], kwargs: dict[str, str], account_name: str
    ) -> dict[str, Any]:
        if not sub:
            return self._error("storage container subcommand required")
        action = sub[0]
        name = kwargs.get("name", "")

        if action == "list":
            return self._ok(
                [
                    {"name": "container1", "properties": {"leaseStatus": "unlocked", "leaseState": "available", "publicAccess": "None"}},
                    {"name": "container2", "properties": {"leaseStatus": "unlocked", "leaseState": "available", "publicAccess": "Blob"}},
                ]
            )

        if action == "create":
            return self._ok(
                {"name": name, "properties": {"leaseStatus": "unlocked", "leaseState": "available", "publicAccess": "None"}, "created": True}
            )

        return self._error(f"unknown container subcommand: {action}")

    def _dispatch_storage_blob(
        self, sub: list[str], kwargs: dict[str, str], account_name: str
    ) -> dict[str, Any]:
        if not sub:
            return self._error("storage blob subcommand required")
        action = sub[0]
        container = kwargs.get("container_name", "")
        blob_name = kwargs.get("name", "")

        if action == "list":
            return self._ok(
                [
                    {"name": "file1.txt", "properties": {"contentLength": 1024, "contentType": "text/plain", "blobType": "BlockBlob", "leaseStatus": "unlocked"}},
                    {"name": "image.png", "properties": {"contentLength": 20480, "contentType": "image/png", "blobType": "BlockBlob", "leaseStatus": "unlocked"}},
                ]
            )

        if action == "upload":
            return self._ok(
                {"name": blob_name, "container": container, "properties": {"contentLength": 0, "blobType": "BlockBlob", "leaseStatus": "unlocked"}, "uploaded": True}
            )

        if action == "delete":
            return self._ok({"deleted": True, "name": blob_name, "container": container})

        return self._error(f"unknown blob subcommand: {action}")

    # ------------------------------------------------------------------
    # Network commands (appgateway, lb, vnet)
    # ------------------------------------------------------------------

    def _dispatch_network(
        self, sub: list[str], kwargs: dict[str, str]
    ) -> dict[str, Any]:
        if not sub:
            return self._error("network subcommand required")
        resource_type = sub[0]
        sub_sub = sub[1:]

        if resource_type == "application-gateway":
            return self._dispatch_appgw(sub_sub, kwargs)
        if resource_type == "lb":
            return self._dispatch_lb(sub_sub, kwargs)
        if resource_type == "vnet":
            return self._dispatch_vnet(sub_sub, kwargs)
        return self._error(f"unknown network resource type: {resource_type}")

    # ---- Application Gateway ----

    def _dispatch_appgw(
        self, sub: list[str], kwargs: dict[str, str]
    ) -> dict[str, Any]:
        if not sub:
            return self._error("application-gateway subcommand required")
        action = sub[0]
        name = kwargs.get("name", "")
        rg = kwargs.get("resource_group", "")

        if action == "create":
            if not name or not rg:
                return self._error("--name and --resource-group required")
            capacity = int(kwargs.get("capacity", "2"))
            sku = kwargs.get("sku", "Standard_v2")
            loc = self._random_location(self._rng_for_data)
            gw: dict[str, Any] = {
                "id": f"/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/{rg}/providers/Microsoft.Network/applicationGateways/{name}",
                "name": name,
                "location": loc,
                "resourceGroup": rg,
                "type": "Microsoft.Network/applicationGateways",
                "sku": {"name": sku, "tier": sku, "capacity": capacity},
                "properties": {
                    "provisioningState": "Succeeded",
                    "operationalState": "Running",
                },
            }
            self._put(rg, name, gw)
            return self._ok(gw)

        if action == "show":
            return self._ok(self._get(rg, name))

        if action == "list":
            return self._ok(self._list_rg(rg))

        if action == "start":
            gw = self._get(rg, name)
            gw["properties"]["operationalState"] = "Running"
            return self._ok({"name": name, "resourceGroup": rg, "status": "Succeeded"})

        if action == "stop":
            gw = self._get(rg, name)
            gw["properties"]["operationalState"] = "Stopped"
            return self._ok({"name": name, "resourceGroup": rg, "status": "Succeeded"})

        if action == "delete":
            if not self._flag_present("yes", sub):
                return self._error("--yes flag required for delete")
            self._delete_res(rg, name)
            return self._ok({"status": "Succeeded", "name": name, "resourceGroup": rg})

        if action == "probe":
            return self._dispatch_appgw_probe(sub[1:], kwargs, name, rg)

        return self._error(f"unknown application-gateway subcommand: {action}")

    def _dispatch_appgw_probe(
        self, sub: list[str], kwargs: dict[str, str], gw_name: str, rg: str
    ) -> dict[str, Any]:
        if not sub:
            return self._error("probe subcommand required")
        action = sub[0]
        probe_name = kwargs.get("name", "probe1")

        if action == "show":
            return self._ok(
                {
                    "name": probe_name,
                    "protocol": "Http",
                    "path": "/health",
                    "interval": 30,
                    "timeout": 30,
                    "unhealthyThreshold": 3,
                    "pickHostNameFromBackendHttpSettings": False,
                    "minServers": 0,
                    "match": {"statusCodes": ["200-399"]},
                }
            )

        return self._error(f"unknown probe subcommand: {action}")

    # ---- Load Balancer ----

    def _dispatch_lb(
        self, sub: list[str], kwargs: dict[str, str]
    ) -> dict[str, Any]:
        if not sub:
            return self._error("lb subcommand required")
        action = sub[0]
        name = kwargs.get("name", "")
        rg = kwargs.get("resource_group", "")
        lb_name = kwargs.get("lb_name", name)

        if action == "create":
            if not name or not rg:
                return self._error("--name and --resource-group required")
            loc = self._random_location(self._rng_for_data)
            lb: dict[str, Any] = {
                "id": f"/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/{rg}/providers/Microsoft.Network/loadBalancers/{name}",
                "name": name,
                "location": loc,
                "resourceGroup": rg,
                "type": "Microsoft.Network/loadBalancers",
                "properties": {"provisioningState": "Succeeded"},
            }
            self._put(rg, name, lb)
            return self._ok(lb)

        if action == "show":
            return self._ok(self._get(rg, name))

        if action == "list":
            return self._ok(self._list_rg(rg))

        if action == "rule":
            return self._dispatch_lb_rule(sub[1:], kwargs, lb_name, rg)

        if action == "probe":
            return self._dispatch_lb_probe(sub[1:], kwargs, lb_name, rg)

        if action == "delete":
            if not self._flag_present("yes", sub):
                return self._error("--yes flag required for delete")
            self._delete_res(rg, name)
            return self._ok({"status": "Succeeded", "name": name, "resourceGroup": rg})

        return self._error(f"unknown lb subcommand: {action}")

    def _dispatch_lb_rule(
        self, sub: list[str], kwargs: dict[str, str], lb_name: str, rg: str
    ) -> dict[str, Any]:
        if not sub:
            return self._error("lb rule subcommand required")
        action = sub[0]
        if action == "list":
            return self._ok(
                [
                    {
                        "name": "HTTPRule",
                        "properties": {
                            "protocol": "Tcp",
                            "frontendPort": 80,
                            "backendPort": 8080,
                            "probe": {"id": f"/subscriptions/.../probes/HTTPProbe"},
                            "provisioningState": "Succeeded",
                        },
                    }
                ]
            )
        return self._error(f"unknown lb rule subcommand: {action}")

    def _dispatch_lb_probe(
        self, sub: list[str], kwargs: dict[str, str], lb_name: str, rg: str
    ) -> dict[str, Any]:
        if not sub:
            return self._error("lb probe subcommand required")
        action = sub[0]
        probe_name = kwargs.get("name", "probe1")

        if action == "create":
            protocol = kwargs.get("protocol", "Http")
            port = kwargs.get("port", "8080")
            return self._ok(
                {
                    "name": probe_name,
                    "properties": {
                        "protocol": protocol,
                        "port": int(port),
                        "intervalInSeconds": 15,
                        "numberOfProbes": 2,
                        "provisioningState": "Succeeded",
                    },
                }
            )

        if action == "list":
            return self._ok(
                [
                    {
                        "name": "HTTPProbe",
                        "properties": {
                            "protocol": "Http",
                            "port": 8080,
                            "intervalInSeconds": 15,
                            "numberOfProbes": 2,
                            "provisioningState": "Succeeded",
                        },
                    }
                ]
            )
        return self._error(f"unknown lb probe subcommand: {action}")

    # ---- VNet ----

    def _dispatch_vnet(
        self, sub: list[str], kwargs: dict[str, str]
    ) -> dict[str, Any]:
        if not sub:
            return self._error("vnet subcommand required")
        action = sub[0]
        name = kwargs.get("name", "")
        rg = kwargs.get("resource_group", "")
        vnet_name = kwargs.get("vnet_name", name)

        if action == "create":
            if not name or not rg:
                return self._error("--name and --resource-group required")
            prefix = kwargs.get("address_prefix", "10.0.0.0/16")
            loc = self._random_location(self._rng_for_data)
            vnet: dict[str, Any] = {
                "id": f"/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/{rg}/providers/Microsoft.Network/virtualNetworks/{name}",
                "name": name,
                "location": loc,
                "resourceGroup": rg,
                "type": "Microsoft.Network/virtualNetworks",
                "properties": {
                    "provisioningState": "Succeeded",
                    "addressSpace": {"addressPrefixes": [prefix]},
                },
            }
            self._put(rg, name, vnet)
            return self._ok(vnet)

        if action == "show":
            return self._ok(self._get(rg, name))

        if action == "list":
            return self._ok(self._list_rg(rg))

        if action == "subnet":
            return self._dispatch_vnet_subnet(sub[1:], kwargs, vnet_name, rg)

        if action == "check-ip-address":
            ip = kwargs.get("ip_address", "10.0.0.1")
            return self._ok(
                {"available": ip.endswith(".1"), "ipAddress": ip}
            )

        if action == "peering":
            return self._dispatch_vnet_peering(sub[1:], kwargs, vnet_name, rg)

        return self._error(f"unknown vnet subcommand: {action}")

    def _dispatch_vnet_subnet(
        self, sub: list[str], kwargs: dict[str, str], vnet_name: str, rg: str
    ) -> dict[str, Any]:
        if not sub:
            return self._error("subnet subcommand required")
        action = sub[0]
        subnet_name = kwargs.get("name", "subnet1")

        if action == "create":
            prefix = kwargs.get("address_prefix", "10.0.1.0/24")
            return self._ok(
                {
                    "name": subnet_name,
                    "properties": {
                        "addressPrefix": prefix,
                        "provisioningState": "Succeeded",
                    },
                }
            )

        if action == "list":
            return self._ok(
                [
                    {
                        "name": "subnet1",
                        "properties": {
                            "addressPrefix": "10.0.1.0/24",
                            "provisioningState": "Succeeded",
                        },
                    },
                    {
                        "name": "subnet2",
                        "properties": {
                            "addressPrefix": "10.0.2.0/24",
                            "provisioningState": "Succeeded",
                        },
                    },
                ]
            )
        return self._error(f"unknown subnet subcommand: {action}")

    def _dispatch_vnet_peering(
        self, sub: list[str], kwargs: dict[str, str], vnet_name: str, rg: str
    ) -> dict[str, Any]:
        if not sub:
            return self._error("peering subcommand required")
        action = sub[0]
        if action == "list":
            return self._ok(
                [
                    {
                        "name": f"{vnet_name}-peer-1",
                        "properties": {
                            "remoteVirtualNetwork": {"id": "/subscriptions/.../virtualNetworks/remote-vnet"},
                            "peeringState": "Connected",
                            "provisioningState": "Succeeded",
                        },
                    }
                ]
            )
        return self._error(f"unknown peering subcommand: {action}")

    # ------------------------------------------------------------------
    # Front Door (AFD) commands
    # ------------------------------------------------------------------

    def _dispatch_afd(
        self, sub: list[str], kwargs: dict[str, str]
    ) -> dict[str, Any]:
        if not sub:
            return self._error("afd subcommand required")
        action = sub[0]
        profile_name = kwargs.get("profile_name", "")
        rg = kwargs.get("resource_group", "")

        if action == "profile":
            return self._dispatch_afd_profile(sub[1:], kwargs, rg)

        if action == "endpoint":
            return self._dispatch_afd_endpoint(sub[1:], kwargs, profile_name, rg)

        return self._error(f"unknown afd subcommand: {action}")

    def _dispatch_afd_profile(
        self, sub: list[str], kwargs: dict[str, str], rg: str
    ) -> dict[str, Any]:
        if not sub:
            return self._error("afd profile subcommand required")
        action = sub[0]
        name = kwargs.get("profile_name", "")

        if action == "create":
            if not name or not rg:
                return self._error("--profile-name and --resource-group required")
            sku = kwargs.get("sku", "Standard_AzureFrontDoor")
            loc = self._random_location(self._rng_for_data)
            profile: dict[str, Any] = {
                "id": f"/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/{rg}/providers/Microsoft.Cdn/profiles/{name}",
                "name": name,
                "location": loc,
                "resourceGroup": rg,
                "type": "Microsoft.Cdn/profiles",
                "sku": {"name": sku},
                "properties": {"provisioningState": "Succeeded"},
            }
            self._put(rg, name, profile)
            return self._ok(profile)

        if action == "show":
            return self._ok(self._get(rg, name))

        if action == "delete":
            if not self._flag_present("yes", sub):
                return self._error("--yes flag required for delete")
            self._delete_res(rg, name)
            return self._ok({"status": "Succeeded", "name": name, "resourceGroup": rg})

        return self._error(f"unknown afd profile subcommand: {action}")

    def _dispatch_afd_endpoint(
        self, sub: list[str], kwargs: dict[str, str], profile_name: str, rg: str
    ) -> dict[str, Any]:
        if not sub:
            return self._error("afd endpoint subcommand required")
        action = sub[0]
        endpoint_name = kwargs.get("endpoint_name", "")

        if action == "show":
            return self._ok(
                {
                    "name": endpoint_name,
                    "profileName": profile_name,
                    "resourceGroup": rg,
                    "properties": {
                        "hostName": f"{endpoint_name}.z01.azurefd.net",
                        "autoGeneratedDomainNameLabelScope": "TenantReuse",
                        "provisioningState": "Succeeded",
                    },
                }
            )

        if action == "purge":
            paths = kwargs.get("content_paths", "/*")
            return self._ok(
                {
                    "name": endpoint_name,
                    "profileName": profile_name,
                    "resourceGroup": rg,
                    "purged": True,
                    "contentPaths": paths.split(",") if isinstance(paths, str) else paths,
                }
            )

        return self._error(f"unknown afd endpoint subcommand: {action}")

    # ------------------------------------------------------------------
    # Key Vault commands
    # ------------------------------------------------------------------

    def _dispatch_keyvault(
        self, sub: list[str], kwargs: dict[str, str]
    ) -> dict[str, Any]:
        if not sub:
            return self._error("keyvault subcommand required")
        action = sub[0]
        name = kwargs.get("name", "")
        rg = kwargs.get("resource_group", "")
        vault_name = kwargs.get("vault_name", name)

        if action == "create":
            if not name or not rg:
                return self._error("--name and --resource-group required")
            loc = self._random_location(self._rng_for_data)
            vault: dict[str, Any] = {
                "id": f"/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/{name}",
                "name": name,
                "location": loc,
                "resourceGroup": rg,
                "type": "Microsoft.KeyVault/vaults",
                "properties": {"provisioningState": "Succeeded", "sku": {"family": "A", "name": "standard"}},
            }
            self._put(rg, name, vault)
            return self._ok(vault)

        if action == "show":
            return self._ok(self._get(rg, name))

        if action == "list":
            return self._ok(self._list_rg(rg))

        if action == "delete":
            if not self._flag_present("yes", sub):
                return self._error("--yes flag required for delete")
            self._delete_res(rg, name)
            return self._ok({"status": "Succeeded", "name": name, "resourceGroup": rg})

        if action == "secret":
            return self._dispatch_keyvault_secret(sub[1:], kwargs, vault_name)

        if action == "key":
            return self._dispatch_keyvault_key(sub[1:], kwargs, vault_name)

        return self._error(f"unknown keyvault subcommand: {action}")

    def _dispatch_keyvault_secret(
        self, sub: list[str], kwargs: dict[str, str], vault_name: str
    ) -> dict[str, Any]:
        if not sub:
            return self._error("keyvault secret subcommand required")
        action = sub[0]

        if action == "list":
            return self._ok(
                [
                    {
                        "id": f"https://{vault_name}.vault.azure.net/secrets/secret1/abc123",
                        "name": "secret1",
                        "attributes": {"enabled": True, "created": "2026-01-01T00:00:00Z", "updated": "2026-01-01T00:00:00Z"},
                    },
                    {
                        "id": f"https://{vault_name}.vault.azure.net/secrets/secret2/def456",
                        "name": "secret2",
                        "attributes": {"enabled": True, "created": "2026-01-02T00:00:00Z", "updated": "2026-01-02T00:00:00Z"},
                    },
                ]
            )

        if action == "show":
            secret_name = kwargs.get("name", "")
            return self._ok(
                {
                    "id": f"https://{vault_name}.vault.azure.net/secrets/{secret_name}/abc123",
                    "name": secret_name,
                    "value": "***mocked-secret-value***",
                    "attributes": {"enabled": True, "created": "2026-01-01T00:00:00Z", "updated": "2026-01-01T00:00:00Z"},
                }
            )

        return self._error(f"unknown secret subcommand: {action}")

    def _dispatch_keyvault_key(
        self, sub: list[str], kwargs: dict[str, str], vault_name: str
    ) -> dict[str, Any]:
        if not sub:
            return self._error("keyvault key subcommand required")
        action = sub[0]

        if action == "list":
            return self._ok(
                [
                    {
                        "kid": f"https://{vault_name}.vault.azure.net/keys/key1/ghi789",
                        "name": "key1",
                        "attributes": {"enabled": True, "created": "2026-01-01T00:00:00Z", "updated": "2026-01-01T00:00:00Z"},
                    }
                ]
            )

        return self._error(f"unknown key subcommand: {action}")


def main() -> None:
    """Simple CLI for testing: ``python3 scripts/mock_azure.py "az vm show ..."``."""
    import sys

    mock = MockAzure()
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/mock_azure.py '<az command>'")
        sys.exit(1)
    result = mock.execute(sys.argv[1])
    import json

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["exit_code"] == 0 else 1)


if __name__ == "__main__":
    main()
