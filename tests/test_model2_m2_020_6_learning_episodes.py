import sqlite3, tempfile
def d():
    p=tempfile.NamedTemporaryFile(suffix=".db",delete=False).name
    with sqlite3.connect(p) as c:c.execute("CREATE TABLE learning_episodes(decision_id INTEGER UNIQUE,execution_id INTEGER,symbol TEXT,created_at INTEGER)");c.commit()
    return p
def i(**k):
    from scripts.model2.persist_training_episodes import persist_learning_episode as f
    return f(**k)
def test_ep_r1_contract_persists():
    assert i(db_path=d(),decision_id=101,execution_id=9001,symbol="BTCUSDT",action_t="OPEN_LONG",state_t={"x":1},reward_t=.1,state_t1={"x":2},done=False,outcome={"s":"FILLED"})["persisted"] is True
def test_ep_r2_hold_persists():
    assert i(db_path=d(),decision_id=102,execution_id=None,symbol="BTCUSDT",action_t="HOLD",state_t={"r":"h"},reward_t=-.01,state_t1={"r":"hh"},done=True,outcome={"s":"NO_ENTRY"})["persisted"] is True
def test_ep_r3_duplicate_blocks():
    p=d();a=dict(db_path=p,decision_id=103,execution_id=9003,symbol="ETHUSDT",action_t="OPEN_SHORT",state_t={"v":"h"},reward_t=.05,state_t1={"v":"m"},done=False,outcome={"s":"PROTECTED"})
    assert i(**a)["persisted"] is True
    r=i(**a);assert r["persisted"] is False and r["reason_code"]=="duplicate_decision_id_blocked"
def test_ep_r4_correlation_saved():
    p=d();i(db_path=p,decision_id=104,execution_id=9004,symbol="SOLUSDT",action_t="CLOSE",state_t={"p":"o"},reward_t=-.02,state_t1={"p":"c"},done=True,outcome={"s":"EXITED"})
    with sqlite3.connect(p) as c:row=c.execute("SELECT decision_id,execution_id,symbol,created_at FROM learning_episodes WHERE decision_id=104").fetchone()
    assert row and row[0]==104 and row[1]==9004 and row[2]=="SOLUSDT" and int(row[3])>0
def test_ep_r5_db_error_fail_safe():
    r=i(db_path="C:/nao/existe/modelo2.db",decision_id=105,execution_id=9005,symbol="BTCUSDT",action_t="OPEN_LONG",state_t={"s":1},reward_t=0.0,state_t1={"s":2},done=False,outcome={"s":"FAILED"})
    assert r["persisted"] is False and r["reason_code"]=="learning_episode_persist_failed" and r["safe_to_continue"] is False
