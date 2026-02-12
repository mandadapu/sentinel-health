-- Seed data for local development
-- Embeddings use zero vectors since local dev uses hash-based embeddings

INSERT INTO clinical_protocols (title, content, embedding, source_type, specialty, effective_date, version)
VALUES
(
    'Respiratory Infection Triage Protocol',
    'SCOPE: Adult patients presenting with acute respiratory symptoms (cough, dyspnea, fever).

TRIAGE CRITERIA:
- ESI Level 1 (Resuscitation): Respiratory failure, SpO2 < 88%, altered mental status
- ESI Level 2 (Emergent): SpO2 88-92%, severe dyspnea at rest, high-risk comorbidities (COPD, CHF, immunocompromised)
- ESI Level 3 (Urgent): SpO2 93-95%, moderate symptoms, stable vitals, needs workup
- ESI Level 4 (Less Urgent): SpO2 > 95%, mild symptoms, low-risk, needs simple evaluation
- ESI Level 5 (Non-Urgent): Mild URI symptoms, no fever, no dyspnea, stable

REQUIRED DIAGNOSTICS BY LEVEL:
- Level 1-2: ABG, CBC, CMP, Blood cultures, CXR, CT if indicated, Respiratory viral panel
- Level 3: CBC, CMP, CXR, Respiratory viral panel
- Level 4-5: Clinical evaluation, rapid strep/flu if indicated

DISPOSITION GUIDELINES:
- Admit: ESI 1-2, ESI 3 with worsening trajectory
- Observe: ESI 3 with uncertain trajectory
- Discharge: ESI 4-5 with clear follow-up plan',
    (SELECT array_agg(0)::vector(1024) FROM generate_series(1, 1024)),
    'hospital_curated',
    'emergency_medicine',
    '2024-01-01',
    1
),
(
    'Cardiac Chest Pain Evaluation Protocol',
    'SCOPE: Adult patients presenting with chest pain or anginal equivalents.

IMMEDIATE ACTIONS:
- 12-lead ECG within 10 minutes of arrival
- Troponin at presentation, repeat at 3 hours
- Aspirin 325mg unless contraindicated

TRIAGE CRITERIA:
- ESI Level 1: STEMI on ECG, hemodynamic instability, cardiac arrest
- ESI Level 2: NSTEMI (troponin positive), ongoing chest pain, dynamic ECG changes, ACS high-risk features (HEART score >= 7)
- ESI Level 3: Chest pain resolved, normal initial ECG, HEART score 4-6, needs serial troponins
- ESI Level 4: Low-risk chest pain (HEART score 0-3), atypical features, young patient
- ESI Level 5: Non-cardiac chest pain, musculoskeletal, clearly benign etiology

HEART SCORE COMPONENTS:
- History (0-2), ECG (0-2), Age (0-2), Risk Factors (0-2), Troponin (0-2)

DISPOSITION:
- STEMI: Cath lab activation
- NSTEMI: Cardiology consult, admit to telemetry
- Intermediate risk: Observation unit, serial troponins
- Low risk: Discharge with cardiology follow-up within 72 hours',
    (SELECT array_agg(0)::vector(1024) FROM generate_series(1, 1024)),
    'hospital_curated',
    'cardiology',
    '2024-01-01',
    1
),
(
    'Sepsis Screening and Early Management Protocol',
    'SCOPE: Adult patients with suspected or confirmed infection and potential sepsis.

SCREENING CRITERIA (qSOFA >= 2):
- Respiratory rate >= 22
- Altered mentation (GCS < 15)
- Systolic BP <= 100 mmHg

TRIAGE CRITERIA:
- ESI Level 1: Septic shock (MAP < 65 despite fluids, lactate > 4)
- ESI Level 2: Sepsis with organ dysfunction (SOFA >= 2), lactate 2-4, hypotension responsive to fluids
- ESI Level 3: Suspected sepsis, stable vitals, needs workup (qSOFA = 1)
- ESI Level 4: Localized infection, no systemic signs

HOUR-1 BUNDLE (for ESI 1-2):
- Blood cultures before antibiotics (do not delay abx > 15 min)
- Broad-spectrum antibiotics
- Lactate level
- 30 mL/kg crystalloid for hypotension or lactate >= 4
- Vasopressors if MAP < 65 after fluid resuscitation

REASSESSMENT:
- Repeat lactate at 2-4 hours if initial > 2
- Reassess volume status and tissue perfusion
- Document response to interventions',
    (SELECT array_agg(0)::vector(1024) FROM generate_series(1, 1024)),
    'hospital_curated',
    'emergency_medicine',
    '2024-01-01',
    1
)
ON CONFLICT DO NOTHING;
