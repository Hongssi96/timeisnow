import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_seoul_baseinfo import summarize


class SeoulBaseinfoTests(unittest.TestCase):
    def response(self, code='0', row=''):
        return f'<ServiceResult><msgHeader><headerCd>{code}</headerCd></msgHeader><msgBody>{row}</msgBody></ServiceResult>'.encode()

    def test_success_is_not_mapping_completion(self):
        result = summarize(self.response(row='<itemList><stId>1</stId><stNm>sample</stNm><arsId>001</arsId><tmX>127</tmX><tmY>37</tmY></itemList>'))
        self.assertEqual(result['status'], 'response_received')
        self.assertTrue(result['identity_fields_present'])
        self.assertTrue(result['geographic_coordinate_ranges_valid'])
        self.assertFalse(result['production_mapping_validated'])
        self.assertFalse(result['coordinate_reference_system_verified'])

    def test_provider_error_is_not_empty_success(self):
        self.assertEqual(summarize(self.response('20'))['status'], 'provider_error')

    def test_empty_success_is_no_stations(self):
        self.assertEqual(summarize(self.response())['status'], 'no_stations')

    def test_missing_identity_and_nonfinite_coordinates(self):
        for value in ('nan', 'inf', '200', 'bad'):
            result = summarize(self.response(row=f'<itemList><tmX>{value}</tmX><tmY>37</tmY></itemList>'))
            self.assertFalse(result['identity_fields_present'])
            self.assertFalse(result['geographic_coordinate_ranges_valid'])


if __name__ == '__main__':
    unittest.main()
