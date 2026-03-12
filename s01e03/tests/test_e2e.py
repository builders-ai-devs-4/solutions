def test_health_check(logger):
    logger.info("TEST: health check")
    import requests
    r = requests.get("http://localhost:8000", timeout=5)
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    logger.info("PASS: health check")


def test_single_message(chat, logger):
    logger.info("TEST: single message")
    data = chat("e2e-single", "Hello, can you help me with a package?")
    assert "msg" in data
    assert isinstance(data["msg"], str)
    assert len(data["msg"]) > 0
    logger.info(f"PASS: single message | response={data['msg']!r}")


def test_check_package_tool(chat, logger):
    logger.info("TEST: check_package tool")
    data = chat("e2e-check", "What is the status of package PKG12345678?")
    assert "msg" in data
    logger.info(f"PASS: check_package | response={data['msg']!r}")


def test_conversation_memory(chat, logger):
    session = "e2e-memory"
    logger.info(f"TEST: conversation memory | session={session}")

    turn1 = chat(session, "I'm asking about package PKG12345678.")
    logger.info(f"Turn 1: {turn1['msg']!r}")

    turn2 = chat(session, "What was the package ID I just mentioned?")
    logger.info(f"Turn 2: {turn2['msg']!r}")

    assert "PKG12345678" in turn2["msg"], (
        f"Agent did not remember package ID. Response: {turn2['msg']!r}"
    )
    logger.info("PASS: conversation memory")


def test_separate_sessions_are_independent(chat, logger):
    logger.info("TEST: session isolation")

    chat("e2e-session-A", "My package ID is PKG-AAAA-1111.")
    data_b = chat("e2e-session-B", "What package ID did I give you?")

    logger.info(f"Session B response: {data_b['msg']!r}")
    assert "PKG-AAAA-1111" not in data_b["msg"], (
        f"Session B leaked data from session A. Response: {data_b['msg']!r}"
    )
    logger.info("PASS: session isolation")

