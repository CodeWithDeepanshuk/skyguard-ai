# Iteration 13 Run Guide — Easy Hinglish

## Abhi status

Code ready hai, lekin Git repository mein private IMD observations intentionally nahi hain. Isliye local machine par Iteration 13 metrics banana possible nahi tha. Fake result banane ke bajay reports mein `NOT ENOUGH GENUINE TEMPORAL DATA FOR THIS EXPERIMENT` likha gaya hai.

## Kaise run karein

1. Pehle Iteration 12 notebook ko regular intervals par run karke genuine IMD snapshots Drive mein collect karein.
2. IMD se timestamp timezone confirm hone ke baad hi Iteration 12/13 flag true karein.
3. Kam-se-kam 50 stations ke 30 distinct days hone par Iteration 13 notebook upload karein.
4. `Runtime → Run all` karein.
5. Last cell se `SkyGuard_Iteration13_SIH26073_Scientific_Validation_Reports.zip` return karein.

Notebook source windows ko pehle train/validation/future/unseen-station parts mein divide karta hai. Uske baad har partition mein alag seed se fault copies banata hai. Isliye same original reading train aur test dono mein nahi ja sakti.

GPU compulsory nahi hai. Current baselines CPU-friendly hain. Deep network tabhi add karna chahiye jab genuine history aur simple baselines se measurable benefit prove ho.
