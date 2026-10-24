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
