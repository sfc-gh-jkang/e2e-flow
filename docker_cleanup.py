"""Prefect flow for Docker cleanup to prevent disk bloat on VMs."""

import subprocess
from prefect import flow, task


@task
def cleanup_containers(keep_containers: int = 10) -> int:
    """Remove old containers, keeping the most recent N."""
    containers_removed = 0
    
    print(f"🧹 Cleaning up containers (keeping last {keep_containers})...")
    result = subprocess.run(
        ["docker", "ps", "-aq"], 
        capture_output=True, text=True, check=False
    )
    containers = [c for c in result.stdout.strip().split("\n") if c]
    
    if len(containers) > keep_containers:
        old_containers = containers[keep_containers:]
        for container_id in old_containers:
            subprocess.run(
                ["docker", "rm", "-f", container_id], 
                capture_output=True, check=False
            )
            containers_removed += 1
        print(f"  ✓ Removed {containers_removed} old containers")
    else:
        print(f"  ℹ️ Only {len(containers)} containers - no cleanup needed")
    
    return containers_removed


@task
def cleanup_images(keep_images: int = 3) -> int:
    """Remove old images, keeping the most recent N."""
    images_removed = 0
    
    print(f"🧹 Cleaning up images (keeping last {keep_images})...")
    result = subprocess.run(
        ["docker", "images", "-q"], 
        capture_output=True, text=True, check=False
    )
    images = [i for i in result.stdout.strip().split("\n") if i]
    
    if len(images) > keep_images:
        old_images = images[keep_images:]
        for image_id in old_images:
            subprocess.run(
                ["docker", "rmi", "-f", image_id], 
                capture_output=True, check=False
            )
            images_removed += 1
        print(f"  ✓ Removed {images_removed} old images")
    else:
        print(f"  ℹ️ Only {len(images)} images - no cleanup needed")
    
    return images_removed


@task
def prune_docker() -> None:
    """Prune dangling images and build cache."""
    print("🧹 Pruning dangling images and build cache...")
    subprocess.run(["docker", "image", "prune", "-f"], capture_output=True, check=False)
    subprocess.run(
        ["docker", "builder", "prune", "-f", "--filter", "until=24h"], 
        capture_output=True, check=False
    )
    print("  ✓ Prune complete")


@flow(log_prints=True)
def docker_cleanup(keep_images: int = 3, keep_containers: int = 10):
    """
    Clean up old Docker images and containers to prevent disk bloat.
    
    This flow is designed to run on Docker work pools where the Docker
    socket is mounted to the container.
    
    Args:
        keep_images: Number of recent images to keep (default: 3)
        keep_containers: Number of recent containers to keep (default: 10)
        
    Requirements:
        - Docker CLI must be installed in the container
        - Docker socket must be mounted: volumes: ["/var/run/docker.sock:/var/run/docker.sock"]
        
    Returns:
        Dict with cleanup statistics
    """
    # Check if Docker is available
    result = subprocess.run(
        ["docker", "--version"], 
        capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        print("⚠️ Docker not available - skipping cleanup")
        print("   Ensure Docker CLI is installed and socket is mounted")
        return {"images_removed": 0, "containers_removed": 0, "status": "skipped"}
    
    print(f"🐳 Docker version: {result.stdout.strip()}")
    
    # Run cleanup tasks
    containers_removed = cleanup_containers(keep_containers)
    images_removed = cleanup_images(keep_images)
    prune_docker()
    
    print(f"\n✓ Cleanup complete!")
    print(f"  Images removed: {images_removed}")
    print(f"  Containers removed: {containers_removed}")
    
    return {
        "images_removed": images_removed, 
        "containers_removed": containers_removed,
        "status": "completed"
    }


if __name__ == "__main__":
    # =========================================================================
    # TESTING DOCKER CLEANUP
    # =========================================================================
    #
    # Test locally:
    #   uv run python docker_cleanup.py
    #
    # Test with custom values:
    #   uv run python -c "from docker_cleanup import docker_cleanup; docker_cleanup(keep_images=1, keep_containers=5)"
    #
    # Run as Prefect deployment:
    #   uv run prefect deployment run 'docker-cleanup/docker-cleanup'
    #
    # =========================================================================
    
    docker_cleanup()

