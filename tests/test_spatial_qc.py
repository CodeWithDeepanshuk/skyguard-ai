import sys
import unittest
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skyguard.features.spatial_qc import add_spatial_qc


class SpatialEvidenceTests(unittest.TestCase):
    def test_support_and_scale_floor(self):
        data={'neighbor_station_count':[3,1,3], 'neighbor_max_age_minutes':[10,10,90]}
        for sensor in ('temperature','pressure','humidity'):
            data.update({f'neighbor_{sensor}_count':[3,1,3],f'neighbor_{sensor}_residual':[10,10,10],f'neighbor_{sensor}_mad':[0,0,0],f'{sensor}_robust_z_24h':[4,4,4]})
        result=add_spatial_qc(pd.DataFrame(data))
        self.assertEqual(result.qc_temperature_buddy_z.iloc[0],10)
        self.assertEqual(result.qc_temperature_temporal_spatial.iloc[0],4)
        self.assertTrue(result.qc_temperature_buddy_z.iloc[1:].isna().all())
        self.assertEqual(result.qc_pressure_buddy_z.iloc[0],5)

if __name__=='__main__': unittest.main()
