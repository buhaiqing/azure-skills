#!/usr/bin/env python3
"""依赖图自动构建器 — 基于 skill 元数据和服务类型推断依赖关系

C-4 复利资产：新增 skill 时自动扩展 dependency_graph.json，无需手工维护。

依赖推断规则：
1. compute 类（vm, aks, aci, function, appservice）→ networking（vnet, nsg, loadbalancer）+ monitor
2. networking 类（vnet, nsg, loadbalancer, appgateway, frontdoor）→ dns, monitor
3. storage 类（blob, file, queue, backup）→ monitor, keyvault（加密）
4. database 类（sqldb, postgres, cosmos, redis）→ vnet, nsg, monitor, keyvault
5. messaging 类（servicebus, eventhub, eventgrid）→ vnet, monitor, keyvault
6. identity 类（keyvault, apim）→ monitor, audit

输入：azure-*-ops/SKILL.md frontmatter
输出：scripts/dependency_graph.json
"""
import json
import re
import sys
from pathlib import Path
from typing import Optional


# 服务类型 → 依赖规则
DEPENDENCY_RULES = {
    "compute": {
        "keywords": ["vm", "aks", "aci", "function", "appservice", "container"],
        "deps": ["azure-vnet-ops", "azure-nsg-ops", "azure-monitor-ops"],
        "conditional": {
            "azure-aks-ops": ["azure-loadbalancer-ops", "azure-acr-ops", "azure-keyvault-ops"],
            "azure-aci-ops": ["azure-acr-ops"],
            "azure-appservice-ops": ["azure-appgateway-ops"],
        }
    },
    "networking": {
        "keywords": ["vnet", "nsg", "loadbalancer", "appgateway", "frontdoor", "trafficmanager", "dns", "privateendpoint"],
        "deps": ["azure-monitor-ops"],
        "conditional": {
            "azure-vnet-ops": ["azure-nsg-ops"],
            "azure-loadbalancer-ops": ["azure-nsg-ops"],
            "azure-appgateway-ops": ["azure-waf-ops"] if False else [],  # WAF not in repo yet
            "azure-frontdoor-ops": ["azure-dns-ops", "azure-trafficmanager-ops"],
            "azure-dns-ops": [],
        }
    },
    "storage": {
        "keywords": ["blobstorage", "file-storage", "queue-storage", "backup"],
        "deps": ["azure-monitor-ops", "azure-keyvault-ops"],
        "conditional": {
            "azure-backup-ops": ["azure-site-recovery-ops"],
        }
    },
    "database": {
        "keywords": ["sqldb", "postgres", "cosmos", "redis"],
        "deps": ["azure-vnet-ops", "azure-nsg-ops", "azure-monitor-ops", "azure-keyvault-ops"],
        "conditional": {}
    },
    "messaging": {
        "keywords": ["servicebus", "eventhub", "eventgrid"],
        "deps": ["azure-vnet-ops", "azure-monitor-ops", "azure-keyvault-ops"],
        "conditional": {}
    },
    "identity": {
        "keywords": ["keyvault", "apim"],
        "deps": ["azure-monitor-ops", "azure-audit-ops"],
        "conditional": {
            "azure-apim-ops": ["azure-vnet-ops", "azure-nsg-ops"],
        }
    },
    "observability": {
        "keywords": ["monitor", "audit", "cost"],
        "deps": [],
        "conditional": {
            "azure-monitor-ops": ["azure-audit-ops"],
        }
    },
}

# 服务类型映射（从 skill name 推断）
SERVICE_TYPE_MAP = {
    "vm": "compute",
    "aks": "compute",
    "aci": "compute",
    "function": "compute",
    "appservice": "compute",
    "vnet": "networking",
    "nsg": "networking",
    "loadbalancer": "networking",
    "appgateway": "networking",
    "frontdoor": "networking",
    "trafficmanager": "networking",
    "dns": "networking",
    "privateendpoint": "networking",
    "blobstorage": "storage",
    "file-storage": "storage",
    "queue-storage": "storage",
    "backup": "storage",
    "sqldb": "database",
    "postgres": "database",
    "cosmos": "database",
    "redis": "database",
    "servicebus": "messaging",
    "eventhub": "messaging",
    "eventgrid": "messaging",
    "keyvault": "identity",
    "apim": "identity",
    "monitor": "observability",
    "audit": "observability",
    "cost": "observability",
    "acr": "compute",  # Container Registry → compute
    "site-recovery": "storage",  # Site Recovery → storage/backup
}

# 服务描述映射
SERVICE_DESC_MAP = {
    "vm": ("Virtual Machines", "VM provisioning, lifecycle, and configuration"),
    "aks": ("Azure Kubernetes Service", "AKS cluster management, node pools, upgrades"),
    "aci": ("Container Instances", "Serverless container instances"),
    "function": ("Functions", "Serverless function execution"),
    "appservice": ("App Service", "Web app and API hosting"),
    "vnet": ("Virtual Network", "Network isolation and connectivity"),
    "nsg": ("Network Security Groups", "Network traffic filtering"),
    "loadbalancer": ("Load Balancer", "L4 load balancing and traffic distribution"),
    "appgateway": ("Application Gateway", "L7 load balancing with WAF"),
    "frontdoor": ("Front Door", "Global L7 load balancing and CDN"),
    "trafficmanager": ("Traffic Manager", "DNS-based traffic routing"),
    "dns": ("DNS", "Domain name resolution"),
    "privateendpoint": ("Private Endpoint", "Private connectivity to PaaS services"),
    "blobstorage": ("Blob Storage", "Object storage for unstructured data"),
    "file-storage": ("File Storage", "Managed file shares (SMB/NFS)"),
    "queue-storage": ("Queue Storage", "Message queuing for async workflows"),
    "backup": ("Backup", "Automated backup and restore"),
    "site-recovery": ("Site Recovery", "Disaster recovery and replication"),
    "sqldb": ("SQL Database", "Managed relational database (SQL Server)"),
    "postgres": ("Database for PostgreSQL", "Managed PostgreSQL database"),
    "cosmos": ("Cosmos DB", "Globally distributed multi-model database"),
    "redis": ("Cache for Redis", "In-memory data store and cache"),
    "servicebus": ("Service Bus", "Enterprise messaging and queuing"),
    "eventhub": ("Event Hubs", "Big data streaming and event ingestion"),
    "eventgrid": ("Event Grid", "Event routing and reactive programming"),
    "keyvault": ("Key Vault", "Secrets, keys, and certificates management"),
    "apim": ("API Management", "API gateway and developer portal"),
    "monitor": ("Monitor", "Metrics, logs, alerts, and diagnostics"),
    "audit": ("Audit", "Compliance and activity log tracking"),
    "cost": ("Cost Management", "Cost analysis and optimization"),
    "acr": ("Container Registry", "Container image storage and management"),
}


def extract_skill_name_from_dir(skill_dir: Path) -> Optional[str]:
    """从目录名提取 skill name: azure-xxx-ops → azure-xxx-ops"""
    if skill_dir.name.startswith("azure-") and skill_dir.name.endswith("-ops"):
        return skill_dir.name
    return None


def extract_short_name(skill_name: str) -> str:
    """提取短名称: azure-vm-ops → vm"""
    return skill_name.replace("azure-", "").replace("-ops", "")


def infer_service_type(short_name: str) -> str:
    """推断服务类型"""
    return SERVICE_TYPE_MAP.get(short_name, "unknown")


def infer_dependencies(skill_name: str, service_type: str) -> list[str]:
    """基于服务类型推断依赖"""
    if service_type not in DEPENDENCY_RULES:
        return ["azure-monitor-ops"]  # 默认依赖 monitor
    
    rules = DEPENDENCY_RULES[service_type]
    deps = list(rules["deps"])
    
    # 添加条件依赖
    conditional = rules.get("conditional", {})
    if skill_name in conditional:
        deps.extend(conditional[skill_name])
    
    # 去重并排除自身
    deps = list(set(deps))
    if skill_name in deps:
        deps.remove(skill_name)
    
    return sorted(deps)


def scan_skills(root_dir: Path) -> list[dict]:
    """扫描所有 azure-*-ops 目录，提取 skill 元数据"""
    skills = []
    
    for skill_dir in sorted(root_dir.glob("azure-*-ops")):
        if not skill_dir.is_dir():
            continue
        
        skill_name = extract_skill_name_from_dir(skill_dir)
        if not skill_name:
            continue
        
        short_name = extract_short_name(skill_name)
        service_type = infer_service_type(short_name)
        deps = infer_dependencies(skill_name, service_type)
        
        # 服务描述
        service_info = SERVICE_DESC_MAP.get(short_name, (short_name.title(), f"{short_name} operations"))
        service_name, description = service_info
        
        skills.append({
            "name": skill_name,
            "short_name": short_name,
            "service_type": service_type,
            "service_name": service_name,
            "description": description,
            "dependencies": deps,
        })
    
    return skills


def build_dependency_graph(skills: list[dict]) -> dict:
    """构建 dependency_graph.json 结构"""
    nodes = {}
    
    for skill in skills:
        nodes[skill["name"]] = {
            "service": skill["service_name"],
            "type": skill["service_type"],
            "direct_deps": skill["dependencies"],
            "description": skill["description"],
        }
    
    # RCA paths（示例：常见故障诊断路径）
    rca_paths = [
        {"skill": "azure-aks-ops", "path": ["azure-vm-ops", "azure-vnet-ops", "azure-nsg-ops", "azure-loadbalancer-ops"]},
        {"skill": "azure-vm-ops", "path": ["azure-vnet-ops", "azure-nsg-ops"]},
        {"skill": "azure-appservice-ops", "path": ["azure-appgateway-ops", "azure-vnet-ops"]},
        {"skill": "azure-frontdoor-ops", "path": ["azure-dns-ops", "azure-trafficmanager-ops"]},
    ]
    
    return {
        "version": "1.1.0",
        "description": "Azure service dependency graph for cross-skill orchestration. Auto-generated by build_dependency_graph.py.",
        "nodes": nodes,
        "rca_paths": rca_paths,
    }


def main():
    """主入口：扫描 skills → 构建图 → 输出 JSON"""
    repo_root = Path(__file__).parent.parent
    output_path = repo_root / "scripts" / "dependency_graph.json"
    
    # 扫描 skills
    skills = scan_skills(repo_root)
    print(f"Scanned {len(skills)} skills")
    
    # 构建图
    graph = build_dependency_graph(skills)
    
    # 输出
    output_path.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated {output_path}")
    print(f"  Nodes: {len(graph['nodes'])}")
    print(f"  RCA paths: {len(graph['rca_paths'])}")
    
    # 统计依赖关系
    total_deps = sum(len(node["direct_deps"]) for node in graph["nodes"].values())
    print(f"  Total dependencies: {total_deps}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
