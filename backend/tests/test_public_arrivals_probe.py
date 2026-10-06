"""Synthetic responses exercise probe boundaries; no external requests."""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
import urllib.error
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_public_arrivals import main, summarize


class PublicProbeTests(unittest.TestCase):
    def test_http_200_payload_error_is_not_success(self):
        result = summarize(b'<ServiceResult><msgHeader><headerCd>7</headerCd></msgHeader></ServiceResult>', 'seoul-bus')
        self.assertEqual(result['status'], 'provider_error')

    def test_normal_empty_gyeonggi_response_has_no_predictions(self):
        result = summarize(json.dumps({'response': {'msgHeader': {'resultCode': 0}, 'msgBody': {}}}), 'gyeonggi-bus')
        self.assertEqual(result['status'], 'no_arrivals')
        self.assertEqual(result['nonnegative_seconds_fields'], 0)
        self.assertFalse(result['identity_fields_present'])

    def test_minutes_do_not_masquerade_as_seconds(self):
        item = {'predictTime1': 5, 'predictTimeSec1': -1, 'stationId': 'a', 'routeId': 'b', 'staOrder': 2, 'routeDestId': 'c'}
        result = summarize(json.dumps({'response': {'msgHeader': {'resultCode': 0}, 'msgBody': {'busArrivalItem': item}}}), 'gyeonggi-bus')
        self.assertEqual(result['nonnegative_seconds_fields'], 0)
        self.assertEqual(result['row_count'], 1)

    def test_subway_missing_direction_and_negative_seconds_are_visible(self):
        result = summarize(json.dumps({'errorMessage': {'code': 'INFO-000'}, 'realtimeArrivalList': [{'barvlDt': '-1', 'recptnDt': '2026-10-06 10:00:00'}]}), 'seoul-subway')
        self.assertEqual(result['nonnegative_seconds_fields'], 0)
        self.assertFalse(result['identity_fields_present'])

    def test_missing_key_makes_no_network_request(self):
        with patch('sys.argv', ['probe', 'seoul-bus']), patch('check_public_arrivals.dotenv_values', return_value={}), patch('check_public_arrivals.urllib.request.build_opener') as network, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(), 1)
            network.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())['status'], 'missing_key')

    def test_https_failure_never_falls_back_to_http(self):
        with patch('sys.argv', ['probe', 'seoul-bus']), patch('check_public_arrivals.dotenv_values', return_value={'DATA_GO_KR_SERVICE_KEY': 'synthetic-test-key'}), patch('check_public_arrivals.urllib.request.build_opener') as network, contextlib.redirect_stdout(io.StringIO()):
            network.return_value.open.side_effect = urllib.error.URLError('synthetic timeout')
            self.assertEqual(main(), 1)
            network.return_value.open.assert_called_once()
            self.assertTrue(network.return_value.open.call_args.args[0].startswith('https://ws.bus.go.kr/'))

    def test_http_option_never_applies_to_gyeonggi(self):
        with patch('sys.argv', ['probe', 'gyeonggi-bus', '--official-http']), patch('check_public_arrivals.dotenv_values', return_value={}), patch('check_public_arrivals.urllib.request.build_opener') as network, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(), 1)
            network.assert_not_called()


if __name__ == '__main__':
    unittest.main()
