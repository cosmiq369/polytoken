import pytest

from polytoken.measure import measure_batch
from polytoken.measurement_report import checked_ratios, check_federation, planted_shares


def inputs():
    return [dict(company='samudra', chat_id=c, turn=t, part=p, native='native', en='english', lang='te')
            for c,t,p in [('__system__',0,'system_prompt'),('one',1,'user'),('one',2,'assistant')]]


def provenance():
    return dict(source_query='SELECT fixture', fetched_at='2026-10-24T00:00:00Z',
                time_window_start='2026-10-24T00:00:00Z', time_window_end='2026-10-24T00:00:00Z')


def test_skipped_tokenizer_is_not_zero_filled():
    def unavailable(spec):
        raise OSError('fixture gated tokenizer')
    def forbidden(*args):
        raise AssertionError('A skipped tokenizer must not be measured')
    rows, batch, elapsed = measure_batch(inputs(), 'missing', 'run', provenance(),
                                       load=unavailable, count=forbidden, fragment=forbidden)
    assert rows == []
    assert batch['status'] == 'skipped' and batch['rows_written'] == 0
    assert batch['reason'] == 'OSError: fixture gated tokenizer'
    assert elapsed >= 0


def test_partial_batch_failure_drops_all_rows():
    calls = iter([10, 4, -1])
    rows, batch, _ = measure_batch(inputs(), 'fixture', 'run', provenance(),
                                  load=lambda s: None, count=lambda *a:next(calls), fragment=lambda *a:0.1)
    assert rows == [] and batch['status'] == 'failed' and batch['rows_written'] == 0


def fake_counts():
    calls = iter([60,20,10,5,30,15])
    rows, batch, _ = measure_batch(inputs(), 'fixture', 'run', provenance(), load=lambda s:None,
                                  count=lambda *a:next(calls), fragment=lambda *a:0.1)
    assert batch['rows_written'] == 6 and batch['status'] == 'completed'
    return rows


def test_ratios_and_shares_match_hand_calculation():
    computed = checked_ratios(fake_counts(), inputs())
    assert {r['part']:r['native_to_english_ratio'] for r in computed} == {'system_prompt':3, 'user':2, 'assistant':2}
    check_federation(computed, computed)
    shares = planted_shares(computed, inputs())[0]
    assert shares['system_share_of_input'] == 60/70
    assert shares['output_share_of_total'] == 30/100


def test_ratio_of_sums_not_average_of_ratios():
    items = inputs()+[dict(company='samudra',chat_id='two',turn=1,part='user',native='native',en='english',lang='te')]
    rows = fake_counts()
    rows += [{**rows[2], 'chat_id':'two','tokens':90}, {**rows[3], 'chat_id':'two','tokens':15}]
    user = next(r for r in checked_ratios(rows,items) if r['part']=='user')
    assert user['native_to_english_ratio'] == (10+90)/(5+15) == 5


@pytest.mark.parametrize('mutation', ['missing_pair', 'duplicate', 'missing_item', 'wrong_language'])
def test_invalid_evidence_is_rejected(mutation):
    rows = fake_counts()
    if mutation == 'missing_pair': rows.pop()
    if mutation == 'duplicate': rows.append(rows[0])
    if mutation == 'missing_item': rows=rows[:-2]
    if mutation == 'wrong_language': rows[0]['lang_variant']='hi'
    with pytest.raises(ValueError):
        checked_ratios(rows,inputs())


def test_federation_arithmetic_mismatch_rejected():
    computed = checked_ratios(fake_counts(),inputs())
    wrong = [{**r,'native_to_english_ratio':999} for r in computed]
    with pytest.raises(ValueError,match='ratio differs'):
        check_federation(wrong,computed)


def accounting_fixture():
    items = inputs() + [dict(company='samudra',chat_id='one',turn=t,part=p,native='native',en='english',lang='te')
                        for t,p in [(3,'user'),(4,'assistant')]]
    calls = iter([100,50,10,5,20,10,5,2,30,15])
    rows, _, _ = measure_batch(items, 'fixture', 'run', provenance(), load=lambda s:None,
                               count=lambda *a:next(calls), fragment=lambda *a:0.1)
    return items,rows


def test_billed_history_matches_hand_computation():
    from polytoken.measurement_report import billed_tokens, billed_shares
    items,counts = accounting_fixture()
    native = next(r for r in billed_tokens(items,counts) if r['lang_variant']=='te')
    assert native['billed_input'] == 245
    assert native['billed_output'] == 50
    assert native['billed_system_input'] == 200
    shares = billed_shares(items,counts)[0]
    assert shares['billed']['system_share_of_input'] == 200/245
    assert shares['billed']['output_share_of_total'] == 50/295
    assert shares['corpus']['input_tokens'] == 115
    assert shares['corpus']['output_tokens'] == 50
    assert shares['english']['billed']['input_tokens'] == 122


def test_unanswered_user_is_not_a_billed_request():
    from polytoken.measurement_report import billed_tokens
    items,counts = accounting_fixture()
    items.append({**items[1], 'turn':5})
    counts.extend([{**counts[2], 'turn':5, 'tokens':700}, {**counts[3], 'turn':5, 'tokens':300}])
    native = next(r for r in billed_tokens(items,counts) if r['lang_variant']=='te')
    assert native['billed_input']==245 and native['billed_output']==50 and native['requests']==2
    assert native['corpus_input']==815


@pytest.mark.parametrize('mutation', ['missing','mixed_run','role','turn'])
def test_accounting_rejects_invalid_evidence(mutation):
    from polytoken.measurement_report import billed_tokens
    items,counts = accounting_fixture()
    if mutation=='missing': counts.pop()
    if mutation=='mixed_run':
        for row in counts[:2]: row['run_id']='different'
    if mutation=='role':
        items[-1]['part']='user'
        for row in counts[-2:]: row['part']='user'
    if mutation=='turn':
        items[-1]['turn']=8
        for row in counts[-2:]: row['turn']=8
    with pytest.raises(ValueError): billed_tokens(items,counts)


def test_chat_bootstrap_repeated_answers_do_not_narrow_interval():
    from polytoken.measurement_report import bootstrap_ratios
    def fixture(repeat):
        items = [inputs()[0]]
        counts = [{**r,'tokens':10} for r in fake_counts()[:2]]
        for chat in range(10):
            for k in range(repeat):
                for role,turn in [('user',2*k+1),('assistant',2*k+2)]:
                    items.append({**inputs()[1], 'chat_id':str(chat),'turn':turn,'part':role})
                    for lang,n in [('te', (chat+1)**2+1),('en',chat+2)]:
                        counts.append({**fake_counts()[0], 'chat_id':str(chat),'turn':turn,'part':role,'lang_variant':lang,'tokens':n})
        return items, counts
    one = bootstrap_ratios(*fixture(1))
    three = bootstrap_ratios(*fixture(3))
    for part in ('assistant','system_prompt'):
        a = next(r for r in one if r['part']==part)
        b = next(r for r in three if r['part']==part)
        assert (a['ci_low'],a['ci_high']) == (b['ci_low'],b['ci_high'])
        assert a['cluster_count']==10 and a['bootstrap_replicates']==2000
    assistant = next(r for r in one if r['part']=='assistant')
    assert assistant['ci_low'] < assistant['native_to_english_ratio'] < assistant['ci_high']


def test_bootstrap_rejects_missing_pairs():
    from polytoken.measurement_report import bootstrap_ratios
    items,counts = accounting_fixture()
    with pytest.raises(ValueError): bootstrap_ratios(items,counts[:-1])
