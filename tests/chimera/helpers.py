"""Chimera test yardımcıları."""


def wire_agent_mock_sock(agent, mock_sock):
    """Mock socket'i aktif HTTPS kanalına bağlar."""
    agent.sock = mock_sock

    https_channel = None
    for _, ch in agent.channel_manager._channels:
        if ch.__class__.__name__ == "HTTPSChannel":
            https_channel = ch
            break

    if https_channel is None and agent.channel_manager._channels:
        https_channel = agent.channel_manager._channels[0][1]

    if https_channel is not None:
        https_channel.sock = mock_sock
        agent.channel_manager.active_channel = https_channel


def clear_agent_mock_sock(agent):
    """Agent ve aktif kanal socket referanslarını temizler."""
    agent.sock = None
    if agent.channel_manager.active_channel is not None:
        agent.channel_manager.active_channel.sock = None
