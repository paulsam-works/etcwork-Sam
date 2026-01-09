async def start_docker_container(docker):
    print("Starting Docker container...")
    await docker.strat()


async def stop_docker_container(docker):
    print("Stopping Docker container...")
    docker.stop()
    print("Docker container stopped.")

    