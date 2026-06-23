"""Host-only YAML load/dump/merge (container code must not import this package)."""

from .engine import dump_document, load_document, merge_service_patch_maps, merge_services, merge_services_with_patches

__all__ = ["dump_document", "load_document", "merge_service_patch_maps", "merge_services", "merge_services_with_patches"]
