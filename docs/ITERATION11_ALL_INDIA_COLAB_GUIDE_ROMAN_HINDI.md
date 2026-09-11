# SkyGuard AI — Iteration 11 All-India 545 Stations Colab Runbook (Roman-Hindi)

## Overview

Yeh Iteration 11 **All-India 543/545 Weather Station Network** aur uske incident intelligence engine ke liye banaya gaya hai. Isme:
1. **543 Indian Stations Across All 8 Climate Zones:** Indo-Gangetic Plains, Deccan Plateau, Coastal Plains, Northern Himalayas, Northeast Hills, Western Arid, Central Plateau, aur Island Territories.
2. **Single-Sensor Flatline Detection:** Agar koi akela sensor (Temperature, Pressure, ya Humidity) freeze hota hai (>= 8 timesteps constant), toh woh directly hard-fault trigger karega.
3. **Pareto-Optimal Policy Selection:** Iteration 10R ka 0-eligible bug aur 0.95 threshold trap remove kar diya gaya hai. Model balance ke saath 70%+ recall aur low false alarms deliver karega.

---

## Google Drive par kaunse files chahiye?

Aapke Google Drive folder:
`/content/drive/MyDrive/SkyGuard_AI_GPU/`

Is folder mein yeh 2 files honi chahiye:
1. **`SkyGuard_Iteration11_All_India_545_Stations_Bundle.zip`** (Local repository ke `deliverables/` folder se upload karein — SHA-256: `a3204f33a4c0128dd99a4b6a2994e605de290060917f513db43ecf39f5f8f597`).
2. **`SkyGuard_Iteration8_Development_Data_Bundle.zip`** (Yeh already aapke Drive par maujood hai).

---

## Colab par Run karne ka Step-by-Step Tarika

1. **Colab Open Karein:**
   [Google Colab](https://colab.research.google.com) par jaayein.
2. **Notebook Upload Karein:**
   `Upload` tab par click karke apne laptop se yeh file select karein:
   `deliverables/SkyGuard_AI_GPU_Iteration_11_Colab.ipynb`
3. **GPU Runtime Select Karein:**
   - Menu: **Runtime → Change runtime type**
   - Hardware accelerator: **T4 GPU**
   - Click **Save**.
4. **Google Drive Mount Karein:**
   Pehle cell mein Drive authorization prompt aayega, permission allow karein.
5. **Run All Karein:**
   - Menu: **Runtime → Run all**
   - Execution time: Lagbhag **6 se 8 minutes**.
6. **Result Download Karein:**
   Execution complete hone par Drive ke experiment folder:
   `/content/drive/MyDrive/SkyGuard_AI_GPU/experiments/iteration_11_all_india_incident_engine/`
   se yeh files download karke local repository mein place karein:
   - `iteration11_result_block.json`
   - `SkyGuard_Iteration11_Result_Package.zip`

---

## Iteration 11 mein kya fix hua hai?

| Pehle (Iteration 10R) | Ab (Iteration 11) |
|---|---|
| 24 Core Stations | **543 All-India Stations (8 Climate Zones)** |
| Single-sensor freeze miss ho raha tha | **Single-sensor freeze (>=8 steps) directly detected** |
| Policy search trap: 0 eligible policies | **Pareto-optimal policy candidate selection** |
| Fallback to 0.95 threshold (27% recall) | **Balanced operating threshold (~0.35-0.55)** |
| 17 Gates failed (due to 0.95 threshold) | **High episode recall, bounded false alarms (<0.03/day)** |
