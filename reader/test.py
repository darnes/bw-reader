import unittest
from StringIO import StringIO
from mindset import check_sum, extract_data, extract_packets, translate_packet, \
    TGAttentionESense, TGMeditationESense, TGPoorSignal, TGBlinkStrength, TGRowDataValue, TGEEGPowerValue


class TestPacketParsing(unittest.TestCase):
    # see page 13 of doc attached
    data_packet = b'\xAA\xAA\x20\x02\x00\x83\x18\x00\x00\x94\x00\x00\x42\x00\x00\x0B\x00\x00\x64\x00\x00\x4D\x00\x00\x3D\x00\x00\x07\x00\x00\x05\x04\x0D\x05\x3D\x34'

    def test_check_sum(self):
        packet_length = ord(self.data_packet[2])
        data = self.data_packet[3: 3 + packet_length]
        check_sum_val = self.data_packet[3 + packet_length]
        self.assertEqual(ord(check_sum_val), check_sum(data))

    def test_data_extraction(self):
        stream_obj = StringIO(self.data_packet)
        extracted_data = list(extract_data(StringIO(self.data_packet)))
        self.assertEqual(len(extracted_data), 1)

        packet_length = ord(self.data_packet[2])
        data = self.data_packet[3: 3 + packet_length]
        self.assertEqual(extracted_data[0], data)

    def test_packets_extraction(self):
        packet_length = ord(self.data_packet[2])
        packets = list(extract_packets(self.data_packet[3: 3 + packet_length]))
        self.assertEqual(packets[0], (0, 2, 0))
        self.assertEqual(packets[1], (0, 131, '\x00\x00\x94\x00\x00\x42\x00\x00\x0B\x00\x00\x64\x00\x00\x4D\x00\x00\x3D\x00\x00\x07\x00\x00\x05'))
        self.assertEqual(packets[2], (0, 4, 13))
        self.assertEqual(packets[3], (0, 5, 61))


    def test_packets_translation(self):
        obj = translate_packet(*(0, 2, 0))
        self.assertIsInstance(obj, TGPoorSignal)
        self.assertEqual(obj.value, 0)

        obj = translate_packet(*(0, 4, 13))
        self.assertIsInstance(obj, TGAttentionESense)
        self.assertEqual(obj.value, 13)

        obj = translate_packet(*(0, 5, 43))
        self.assertIsInstance(obj, TGMeditationESense)
        self.assertEqual(obj.value, 43)

        obj = translate_packet(*(0, 22, 51)) # 22 is 0x16
        self.assertIsInstance(obj, TGBlinkStrength)
        self.assertEqual(obj.value, 51)

        #print translate_packet(*(0, 5, 61))
        obj = translate_packet(*(0, 131, '\x00\x00\x94\x00\x00\x42\x00\x00\x0B\x00\x00\x64\x00\x00\x4D\x00\x00\x3D\x00\x00\x07\x00\x00\x05'))
        self.assertIsInstance(obj, TGEEGPowerValue)
        self.assertEqual(obj.value, (148, 66, 11, 100, 77, 61, 7, 5))
        #TGRowDataValue




if __name__ == '__main__':
    unittest.main()