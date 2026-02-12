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
),
(
    'Acute Stroke Assessment Protocol',
    'SCOPE: Adult patients presenting with focal neurological deficits or suspected cerebrovascular accident.

TIME-CRITICAL ACTIONS:
- Door-to-CT target: < 25 minutes
- Door-to-needle (tPA) target: < 60 minutes
- Last known well time documentation is mandatory

TRIAGE CRITERIA:
- ESI Level 1: Active neurological deterioration, GCS < 8, signs of herniation, respiratory compromise
- ESI Level 2: Acute focal deficit within 24 hours onset, NIHSS >= 4, symptom onset < 4.5 hours (tPA candidate), large vessel occlusion suspected
- ESI Level 3: Focal deficit > 24 hours, TIA (resolved symptoms), NIHSS 1-3 with stable presentation
- ESI Level 4: Remote stroke history with new non-acute complaint, minor sensory symptoms
- ESI Level 5: Follow-up for known stable cerebrovascular disease

NIHSS SCORE INTERPRETATION:
- 0: No deficit
- 1-4: Minor stroke
- 5-15: Moderate stroke
- 16-20: Moderate-severe stroke
- 21-42: Severe stroke

REQUIRED DIAGNOSTICS BY LEVEL:
- Level 1-2: Stat non-contrast CT head, CTA head/neck, CBC, CMP, PT/INR, glucose, type and screen
- Level 3: CT head, vascular imaging, standard labs
- Level 4-5: Clinical evaluation, outpatient imaging referral

THROMBOLYTIC CRITERIA (tPA):
- Inclusion: Ischemic stroke, onset < 4.5 hours, NIHSS >= 4, age >= 18
- Exclusion: Active bleeding, INR > 1.7, platelets < 100K, BP > 185/110 uncontrolled, recent surgery < 14 days

DISPOSITION:
- ESI 1-2: Stroke unit or ICU, neurology consult stat
- ESI 3: Admit for expedited workup
- ESI 4-5: Outpatient neurology follow-up within 7 days',
    (SELECT array_agg(0)::vector(1024) FROM generate_series(1, 1024)),
    'hospital_curated',
    'neurology',
    '2024-01-01',
    1
),
(
    'Pediatric Fever Evaluation Protocol',
    'SCOPE: Pediatric patients (0-18 years) presenting with fever (temperature >= 38.0C / 100.4F).

AGE-STRATIFIED TRIAGE CRITERIA:

Neonates (0-28 days):
- ESI Level 2 (always): Any fever >= 38.0C requires full sepsis workup regardless of appearance. Rochester criteria do not apply to this age group.

Infants (29-90 days):
- ESI Level 2: Fever >= 38.0C with ill appearance, prematurity, chronic medical conditions
- ESI Level 3: Fever >= 38.0C, well-appearing, meets low-risk criteria (Rochester: WBC 5-15K, band count < 1500, normal UA, < 5 WBC/hpf stool if diarrhea)

Infants/Toddlers (3-36 months):
- ESI Level 2: Fever >= 39.0C with toxic appearance, petechial rash, bulging fontanelle, immunocompromised
- ESI Level 3: Fever >= 39.0C, well-appearing, no source identified, incomplete immunizations
- ESI Level 4: Fever with identifiable viral source (URI, viral exanthem), well-appearing, immunizations up to date
- ESI Level 5: Low-grade fever, well-appearing, clear viral illness

Children (> 36 months):
- ESI Level 2: Fever with meningeal signs, petechiae, hemodynamic instability, immunocompromised
- ESI Level 3: Fever >= 39.0C without clear source, needs workup
- ESI Level 4: Fever with clear source (pharyngitis, otitis), well-appearing
- ESI Level 5: Low-grade fever, well-appearing, no distress

REQUIRED DIAGNOSTICS BY AGE AND LEVEL:
- 0-28 days: CBC, blood culture, UA with culture, LP (CSF studies), CXR if respiratory symptoms
- 29-90 days ESI 2: Same as neonate workup
- 29-90 days ESI 3: CBC, UA, blood culture; LP if WBC abnormal
- 3-36 months ESI 2-3: CBC, UA, blood culture if unimmunized
- > 36 months: Guided by clinical presentation

DISPOSITION:
- 0-28 days: Admit for IV antibiotics pending cultures (48-hour rule)
- 29-90 days high risk: Admit for observation and IV antibiotics
- 29-90 days low risk: Consider discharge with 24-hour follow-up if reliable family
- Older children: Discharge with return precautions if well-appearing with identified source',
    (SELECT array_agg(0)::vector(1024) FROM generate_series(1, 1024)),
    'hospital_curated',
    'pediatrics',
    '2024-01-01',
    1
),
(
    'Obstetric Emergency Triage Protocol',
    'SCOPE: Pregnant patients (any gestational age) presenting with obstetric or pregnancy-related complaints.

TRIAGE CRITERIA:
- ESI Level 1: Eclamptic seizure, massive hemorrhage (estimated blood loss > 1500 mL), perimortem cesarean indication, uterine rupture, cord prolapse with fetal bradycardia
- ESI Level 2: Severe preeclampsia (BP >= 160/110 with symptoms), placental abruption (painful bleeding + fetal distress), preterm labor < 34 weeks with cervical change, HELLP syndrome (platelets < 100K, elevated LFTs, hemolysis), non-reassuring fetal heart rate pattern
- ESI Level 3: Preeclampsia without severe features (BP 140-159/90-109), preterm contractions without cervical change, PPROM (premature rupture of membranes), second/third trimester bleeding (stable), decreased fetal movement with reactive NST
- ESI Level 4: First trimester bleeding (stable, no hemodynamic compromise), hyperemesis without dehydration, round ligament pain, Braxton-Hicks contractions
- ESI Level 5: Routine pregnancy complaints, medication refill, prenatal lab review

CRITICAL LAB PANEL (ESI 1-2):
- CBC with platelets, CMP (AST, ALT, creatinine), LDH, uric acid, fibrinogen, PT/INR, type and screen, Kleihauer-Betke if Rh-negative

HELLP DIAGNOSTIC CRITERIA:
- Hemolysis: LDH > 600, schistocytes on smear
- Elevated Liver enzymes: AST > 70
- Low Platelets: < 100,000

MAGNESIUM SULFATE PROTOCOL:
- Loading dose: 4-6g IV over 15-20 minutes
- Maintenance: 1-2g/hour continuous infusion
- Monitor: reflexes, respiratory rate >= 12, urine output >= 30 mL/hr
- Toxicity antidote: Calcium gluconate 1g IV

DISPOSITION:
- ESI 1: OR for emergent delivery, MFM and anesthesia stat
- ESI 2: L&D admission, continuous fetal monitoring, MFM consult
- ESI 3: L&D observation, serial assessment
- ESI 4-5: Outpatient follow-up with OB within 48-72 hours',
    (SELECT array_agg(0)::vector(1024) FROM generate_series(1, 1024)),
    'hospital_curated',
    'obstetrics',
    '2024-01-01',
    1
),
(
    'Trauma Triage and Activation Protocol',
    'SCOPE: Patients presenting with traumatic injuries from blunt or penetrating mechanisms.

ACTIVATION LEVELS:

LEVEL 1 (Full Trauma Activation — attending surgeon, anesthesia, OR on standby):
- GCS <= 8
- Intubated patients transferred from field
- Penetrating injury to head, neck, chest, abdomen, or groin
- Systolic BP < 90 mmHg
- Gunshot wound to torso
- Amputation proximal to wrist or ankle
- Paralysis (suspected spinal cord injury)

LEVEL 2 (Modified Trauma Activation — trauma team, surgeon available within 15 min):
- GCS 9-13
- Flail chest
- Two or more proximal long bone fractures
- Pelvic fracture (suspected unstable)
- Open or depressed skull fracture
- Ejection from vehicle
- Pedestrian struck at > 20 mph
- Fall > 20 feet (adults) or > 10 feet (children)

TRIAGE CRITERIA (ESI Mapping):
- ESI Level 1: Level 1 trauma activation criteria met
- ESI Level 2: Level 2 trauma activation criteria met OR high-energy mechanism with concerning vitals
- ESI Level 3: Moderate mechanism, stable vitals, needs imaging and workup (e.g., MVC with seatbelt, isolated extremity fracture with neurovascular compromise)
- ESI Level 4: Minor mechanism, isolated injury, stable (e.g., simple laceration, minor contusion, sprain)
- ESI Level 5: Minor abrasion, resolved symptoms, follow-up only

CDC FIELD TRIAGE CRITERIA (Step 1-4):
- Step 1: Physiologic (GCS, SBP, RR)
- Step 2: Anatomic (penetrating injuries, flail chest, amputation, skull fracture)
- Step 3: Mechanism (falls, vehicle speed, ejection, pedestrian/cyclist struck)
- Step 4: Special considerations (age > 55, anticoagulants, pregnancy, burns)

REQUIRED DIAGNOSTICS:
- Level 1: Trauma panel (CBC, CMP, coags, type and crossmatch, lactate, ETOH, tox screen), FAST exam, trauma CT (head, c-spine, chest, abdomen/pelvis), CXR, pelvic XR
- Level 2: Same as Level 1, may defer based on mechanism
- Level 3: Targeted imaging based on mechanism and exam findings
- Level 4-5: Focused exam and imaging as indicated

DISPOSITION:
- Level 1: ICU or OR depending on findings
- Level 2: Trauma service admission, step-down or floor
- Level 3: Admit or observe based on imaging
- Level 4-5: Discharge with orthopedic or surgical follow-up as needed',
    (SELECT array_agg(0)::vector(1024) FROM generate_series(1, 1024)),
    'hospital_curated',
    'trauma',
    '2024-01-01',
    1
),
(
    'Toxicology Overdose Management Protocol',
    'SCOPE: Patients presenting with known or suspected toxic ingestion, exposure, or overdose.

TOXIDROME RECOGNITION:

Sympathomimetic (cocaine, amphetamines, MDMA):
- Signs: Tachycardia, hypertension, hyperthermia, mydriasis, diaphoresis, agitation
- Treatment: Benzodiazepines for agitation/seizures, active cooling, avoid beta-blockers

Opioid (heroin, fentanyl, oxycodone):
- Signs: Miosis, respiratory depression, bradycardia, CNS depression
- Treatment: Naloxone 0.4-2mg IV/IM, may repeat q2-3 min, consider infusion

Anticholinergic (diphenhydramine, TCAs, jimsonweed):
- Signs: Tachycardia, mydriasis, dry skin, urinary retention, altered mental status, hyperthermia
- Treatment: Physostigmine 0.5-2mg IV slow push (if no conduction delays)

Cholinergic (organophosphates, nerve agents):
- Signs: SLUDGE/BBB (salivation, lacrimation, urination, defecation, GI distress, emesis / bradycardia, bronchospasm, bronchorrhea)
- Treatment: Atropine 2mg IV q3-5 min until secretions dry, pralidoxime 1-2g IV

Sedative-Hypnotic (benzodiazepines, barbiturates, ethanol):
- Signs: CNS depression, respiratory depression, hypotension, hypothermia
- Treatment: Supportive care, flumazenil ONLY if known pure benzodiazepine OD (risk of seizures)

TRIAGE CRITERIA:
- ESI Level 1: Respiratory failure, hemodynamic instability, seizures, severe hyperthermia (> 41C), cardiac arrest, GCS < 8
- ESI Level 2: Altered mental status, HR > 150 or < 50, suspected toxic ingestion within 1 hour (decontamination window), QRS > 120ms on ECG, metabolic acidosis (pH < 7.2)
- ESI Level 3: Alert and oriented, stable vitals, intentional ingestion requiring observation period, toxicology workup needed
- ESI Level 4: Minor accidental exposure, asymptomatic, low-toxicity substance
- ESI Level 5: Remote exposure, asymptomatic, Poison Control clearance

DECONTAMINATION:
- Activated charcoal: Within 1 hour of ingestion, intact airway, cooperative patient
- Whole bowel irrigation: Sustained-release preparations, body packing, iron, lithium
- Do NOT induce emesis (ipecac is obsolete)

REQUIRED DIAGNOSTICS:
- Level 1-2: ECG (QRS, QTc), BMP (anion gap), serum osmolality (osmol gap), acetaminophen level, salicylate level, ethanol level, CBC, hepatic panel, urinalysis, urine drug screen, specific drug levels as indicated
- Level 3: ECG, BMP, acetaminophen/salicylate levels, targeted drug levels
- Level 4-5: Clinical evaluation, Poison Control consultation

DISPOSITION:
- ESI 1: ICU admission, toxicology consult
- ESI 2: Monitored bed, serial ECGs, toxicology consult
- ESI 3: ED observation (4-6 hours minimum), psychiatric evaluation if intentional
- ESI 4-5: Discharge with Poison Control follow-up',
    (SELECT array_agg(0)::vector(1024) FROM generate_series(1, 1024)),
    'hospital_curated',
    'toxicology',
    '2024-01-01',
    1
),
(
    'Psychiatric Emergency Assessment Protocol',
    'SCOPE: Patients presenting with acute psychiatric complaints including suicidal ideation, psychosis, agitation, or behavioral emergencies.

MEDICAL CLEARANCE (must complete before psychiatric disposition):
- Vital signs within normal limits
- Glucose check (rule out hypoglycemia)
- Urine drug screen
- BAL if alcohol suspected
- Basic metabolic panel for patients on psychiatric medications
- TSH if new-onset psychosis
- CT head if new focal neurological findings, head trauma, or first-episode psychosis > age 50

TRIAGE CRITERIA:
- ESI Level 1: Active violence requiring physical restraint, active self-harm in progress, severe neuroleptic malignant syndrome, serotonin syndrome, lethal means in possession
- ESI Level 2: Command auditory hallucinations to harm self/others, high-lethality suicide attempt (hanging, GSW, jumping, toxic ingestion), acute psychosis with inability to care for self, severe agitation requiring chemical restraint
- ESI Level 3: Suicidal ideation with plan but no immediate access to means, psychotic symptoms (stable), acute anxiety/panic attack, involuntary hold criteria met, medication non-compliance with decompensation
- ESI Level 4: Suicidal ideation without plan or intent, medication refill for stable psychiatric condition, chronic anxiety/depression with mild exacerbation
- ESI Level 5: Referral request, follow-up from recent psychiatric visit, stable patient seeking outpatient resources

COLUMBIA SUICIDE SEVERITY RATING SCALE (C-SSRS) — SCREENING QUESTIONS:
1. Wish to be dead? (passive ideation)
2. Non-specific active suicidal thoughts?
3. Active suicidal ideation with any methods (not plan)?
4. Active suicidal ideation with some intent to act?
5. Active suicidal ideation with specific plan and intent?
- Questions 4-5 positive: HIGH RISK — ESI 2, 1:1 observation, psychiatry stat consult
- Questions 2-3 positive: MODERATE RISK — ESI 3, safety precautions, psychiatric evaluation
- Question 1 only: LOW RISK — ESI 4, clinical assessment, safety planning

AGITATION MANAGEMENT:
- Verbal de-escalation first (speak calmly, offer choices, reduce stimulation)
- Voluntary oral medication: Olanzapine 5-10mg ODT or Lorazepam 1-2mg
- Chemical restraint if imminent danger: Haloperidol 5mg + Lorazepam 2mg + Diphenhydramine 50mg IM (B52)
- Physical restraint: Last resort, requires physician order, Q15 min monitoring, reassess Q1 hour

INVOLUNTARY HOLD CRITERIA:
- Danger to self (active suicidal ideation with plan/intent)
- Danger to others (homicidal ideation with identified target and plan)
- Gravely disabled (unable to provide food, clothing, shelter due to mental illness)

DISPOSITION:
- ESI 1-2: Inpatient psychiatric admission or transfer to psychiatric facility
- ESI 3: Psychiatric evaluation, possible admission or crisis stabilization unit
- ESI 4: Outpatient psychiatric referral, safety plan documentation, crisis hotline information
- ESI 5: Outpatient resources, return precautions',
    (SELECT array_agg(0)::vector(1024) FROM generate_series(1, 1024)),
    'hospital_curated',
    'psychiatry',
    '2024-01-01',
    1
),
(
    'Infectious Disease Isolation Protocol',
    'SCOPE: Patients presenting with known or suspected communicable diseases requiring infection control measures.

ISOLATION CATEGORIES AND PRECAUTIONS:

AIRBORNE PRECAUTIONS (negative pressure room required):
- Tuberculosis (pulmonary or laryngeal): Cough > 2 weeks, hemoptysis, night sweats, weight loss, exposure history, immunocompromised
- Measles: Fever, cough, coryza, conjunctivitis, maculopapular rash (cephalocaudal spread), Koplik spots
- Varicella (chickenpox): Vesicular rash in different stages, fever, pruritus
- Disseminated herpes zoster (immunocompromised patients)
- N95 respirator required for all healthcare workers entering room

DROPLET PRECAUTIONS (surgical mask within 6 feet):
- Influenza: Fever, myalgia, cough, rhinorrhea during flu season
- Pertussis: Paroxysmal cough > 2 weeks, post-tussive vomiting, inspiratory whoop
- Meningococcal disease: Petechial rash, meningeal signs, septic appearance
- Mumps: Parotid swelling, fever
- Rubella: Maculopapular rash, lymphadenopathy, arthralgias
- COVID-19 (per current institutional policy)

CONTACT PRECAUTIONS (gown + gloves for all interactions):
- C. difficile: Diarrhea (>= 3 unformed stools/24h), recent antibiotic use, hospitalization history
- MRSA: Known colonization/infection, wounds with purulent drainage
- VRE: Known colonization, high-risk patient (ICU, transplant, hemodialysis)
- Scabies: Pruritic rash, burrows in web spaces, institutional exposure
- Norovirus: Acute onset vomiting/diarrhea, institutional outbreak setting

HIGH-CONSEQUENCE PATHOGEN SCREENING:
- Travel history: Sub-Saharan Africa, Southeast Asia, South America within 21 days
- Symptoms: Fever >= 38.6C + hemorrhagic manifestations (bleeding, bruising, bloody diarrhea)
- Pathogens: Ebola, Marburg, Lassa fever, CCHF
- Action: IMMEDIATE isolation, contact infection control officer, do NOT perform routine labs until cleared

TRIAGE CRITERIA:
- ESI Level 1: Suspected high-consequence pathogen with hemorrhagic manifestations, respiratory failure requiring intubation with airborne pathogen
- ESI Level 2: Active TB with hemoptysis, meningococcal sepsis, febrile neutropenic patient with new infection, suspected high-consequence pathogen (afebrile but exposure history)
- ESI Level 3: Suspected TB (stable), influenza requiring admission, new C. diff infection, chickenpox in immunocompromised patient
- ESI Level 4: Influenza (stable, outpatient management), localized MRSA abscess, scabies
- ESI Level 5: Screening for TB exposure (asymptomatic), follow-up of treated infection

REQUIRED DIAGNOSTICS:
- Level 1-2: CBC, CMP, blood cultures x2, specific pathogen testing (AFB smear/culture, respiratory panel, meningococcal PCR), CXR, procalcitonin
- Level 3: Targeted testing based on suspected pathogen, C. diff toxin PCR, influenza/COVID rapid test
- Level 4-5: Focused clinical evaluation, rapid testing as indicated

DISPOSITION:
- High-consequence pathogen: Designated biocontainment unit (transfer if not available)
- Airborne: Negative pressure room admission
- Droplet/contact: Appropriate isolation room on designated unit
- ESI 4-5: Discharge with infection control instructions and public health notification if reportable',
    (SELECT array_agg(0)::vector(1024) FROM generate_series(1, 1024)),
    'hospital_curated',
    'infectious_disease',
    '2024-01-01',
    1
),
(
    'FHIR ClinicalGuideline: Hypertension Management',
    'SOURCE: FHIR R4 ClinicalGuideline resource — ACC/AHA 2017 Hypertension Guidelines

SCOPE: Adult patients presenting with elevated blood pressure or hypertensive emergency.

BLOOD PRESSURE CLASSIFICATION (ACC/AHA 2017):
- Normal: < 120/80 mmHg
- Elevated: 120-129 / < 80 mmHg
- Stage 1 HTN: 130-139 / 80-89 mmHg
- Stage 2 HTN: >= 140/90 mmHg
- Hypertensive Crisis: > 180/120 mmHg

TRIAGE CRITERIA:
- ESI Level 1: Hypertensive emergency with acute end-organ damage (aortic dissection, acute MI, stroke, pulmonary edema, eclampsia, hypertensive encephalopathy)
- ESI Level 2: Hypertensive urgency (> 180/120) with symptoms (headache, visual changes, chest pain, dyspnea) but no acute end-organ damage
- ESI Level 3: Stage 2 HTN with new symptoms or medication non-compliance, needs workup for secondary causes
- ESI Level 4: Stage 1-2 HTN, asymptomatic, medication adjustment needed
- ESI Level 5: Elevated BP, routine follow-up, lifestyle counseling

HYPERTENSIVE EMERGENCY MANAGEMENT:
- Target: Reduce MAP by no more than 25% in first hour
- IV agents: Nicardipine 5mg/hr (titrate q5min, max 15mg/hr), Labetalol 20mg IV bolus then infusion, Nitroprusside (last resort, cyanide toxicity risk)
- Specific scenarios: Aortic dissection target SBP < 120 within 20 min (esmolol preferred)

REQUIRED DIAGNOSTICS:
- Level 1-2: CBC, CMP (creatinine, electrolytes), troponin, BNP, UA, ECG, CXR, CT head if neurological symptoms, CT angiography if dissection suspected
- Level 3: CMP, UA, ECG, lipid panel, HbA1c, TSH if new diagnosis
- Level 4-5: BP recheck after 5 min rest, review home medications

DISPOSITION:
- Hypertensive emergency: ICU admission, arterial line monitoring
- Hypertensive urgency with symptoms: ED observation, oral antihypertensive, reassess in 4-6 hours
- Stage 1-2 asymptomatic: Outpatient follow-up within 1-2 weeks, lifestyle modifications',
    (SELECT array_agg(0)::vector(1024) FROM generate_series(1, 1024)),
    'fhir_public',
    'cardiology',
    '2024-01-01',
    1
),
(
    'FHIR ClinicalGuideline: Asthma Exacerbation',
    'SOURCE: FHIR R4 ClinicalGuideline resource — NAEPP EPR-3 / GINA 2023

SCOPE: Patients presenting with acute asthma exacerbation or status asthmaticus.

SEVERITY ASSESSMENT:
- Mild: Speaks in sentences, HR < 120, SpO2 > 95%, PEF > 70% predicted, accessory muscle use absent
- Moderate: Speaks in phrases, HR 120-150, SpO2 91-95%, PEF 40-69% predicted, some accessory muscle use
- Severe: Speaks in words only, HR > 150, SpO2 < 91%, PEF < 40% predicted, significant accessory muscle use, diaphoresis
- Life-threatening: Drowsy/confused, bradycardia, silent chest, SpO2 < 85%, PEF unmeasurable

TRIAGE CRITERIA:
- ESI Level 1: Life-threatening exacerbation, respiratory arrest, intubated, altered mental status, silent chest
- ESI Level 2: Severe exacerbation (speaks in words, SpO2 < 91%, PEF < 40%), status asthmaticus (no improvement with initial bronchodilator)
- ESI Level 3: Moderate exacerbation (speaks in phrases, SpO2 91-95%, PEF 40-69%), history of ICU admission for asthma
- ESI Level 4: Mild exacerbation (speaks in sentences, SpO2 > 95%, PEF > 70%), needs nebulizer treatment
- ESI Level 5: Well-controlled asthma, medication refill, routine follow-up

TREATMENT PROTOCOL:
- Mild-Moderate: Albuterol 2.5mg nebulizer q20min x 3, ipratropium 0.5mg with first nebulizer, prednisone 40-60mg PO
- Severe: Continuous albuterol nebulizer, ipratropium q20min x 3, methylprednisolone 125mg IV, magnesium sulfate 2g IV over 20 min
- Life-threatening: Above + consider IV terbutaline, ketamine for intubation (bronchodilator properties), heliox, BiPAP before intubation if possible

REQUIRED DIAGNOSTICS:
- Level 1-2: ABG, CBC, CMP, CXR, peak flow (if able), VBG if ABG not feasible
- Level 3: Peak flow pre/post treatment, SpO2 monitoring, CXR if fever or first presentation
- Level 4-5: Peak flow, SpO2, clinical assessment

DISPOSITION:
- Level 1: ICU, consider intubation (ketamine RSI preferred)
- Level 2: Admit to monitored bed, respiratory therapy consult
- Level 3: ED observation 4-6 hours, reassess PEF. Admit if PEF < 50% after treatment
- Level 4: Discharge if PEF > 70% post-treatment, prescribe 5-day prednisone burst, ensure inhaler technique
- Level 5: Outpatient management, asthma action plan review',
    (SELECT array_agg(0)::vector(1024) FROM generate_series(1, 1024)),
    'fhir_public',
    'emergency_medicine',
    '2024-01-01',
    1
),
(
    'FHIR ClinicalGuideline: Diabetic Ketoacidosis',
    'SOURCE: FHIR R4 ClinicalGuideline resource — ADA Standards of Care 2024

SCOPE: Patients presenting with suspected or confirmed diabetic ketoacidosis (DKA) or hyperglycemic hyperosmolar state (HHS).

DIAGNOSTIC CRITERIA:

DKA:
- Blood glucose > 250 mg/dL (or euglycemic DKA with SGLT2 inhibitor use: glucose may be < 250)
- Arterial pH < 7.30
- Serum bicarbonate < 18 mEq/L
- Anion gap > 12
- Positive serum or urine ketones

DKA SEVERITY:
- Mild: pH 7.25-7.30, bicarb 15-18, alert
- Moderate: pH 7.00-7.24, bicarb 10-14, alert/drowsy
- Severe: pH < 7.00, bicarb < 10, obtunded/comatose

HHS:
- Blood glucose > 600 mg/dL
- Serum osmolality > 320 mOsm/kg
- pH > 7.30
- Minimal ketones
- Altered mental status

TRIAGE CRITERIA:
- ESI Level 1: Severe DKA (pH < 7.0), HHS with coma, Kussmaul respirations with hemodynamic instability, cardiac arrhythmia from hyperkalemia
- ESI Level 2: Moderate DKA (pH 7.0-7.24), HHS (glucose > 600, osmolality > 320), altered mental status, severe dehydration, potassium < 3.3 or > 6.0
- ESI Level 3: Mild DKA (pH 7.25-7.30), new-onset diabetes with ketosis, hyperglycemia > 400 with symptoms (polyuria, polydipsia, vomiting)
- ESI Level 4: Hyperglycemia 250-400 without ketosis, stable, medication adjustment needed
- ESI Level 5: Routine diabetes follow-up, glucose monitoring education

DKA MANAGEMENT PROTOCOL:
1. Fluid resuscitation: NS 1-1.5 L/hr first hour, then 250-500 mL/hr. Switch to D5 1/2 NS when glucose < 200
2. Insulin: Regular insulin 0.1 units/kg/hr IV infusion (do NOT bolus). Do NOT start until K >= 3.3
3. Potassium: If K < 3.3: hold insulin, give 40 mEq/hr. If K 3.3-5.3: add 20-40 mEq per liter of fluid. If K > 5.3: hold potassium, recheck q2h
4. Bicarbonate: Only if pH < 6.9 (100 mEq in 400 mL water with 20 mEq KCl over 2 hours)
5. Monitor: BMP q2h, VBG/ABG q2-4h, strict I/O, q1h glucose

RESOLUTION CRITERIA:
- DKA resolved: glucose < 200, pH > 7.30, bicarb >= 15, anion gap <= 12
- Transition to SubQ insulin: give SubQ dose 1-2 hours BEFORE stopping IV insulin

REQUIRED DIAGNOSTICS:
- Level 1-2: BMP, CBC, VBG/ABG, serum ketones (beta-hydroxybutyrate), serum osmolality, UA, ECG, phosphorus, magnesium, lipase if abdominal pain
- Level 3: BMP, UA, serum ketones, VBG
- Level 4-5: Fingerstick glucose, BMP, HbA1c

DISPOSITION:
- Severe DKA/HHS: ICU admission, endocrinology consult
- Moderate DKA: Step-down or monitored bed, insulin drip protocol
- Mild DKA: Observation, may treat in ED with IV fluids and SubQ insulin if close monitoring available
- Hyperglycemia without DKA: Discharge with medication adjustment and endocrinology follow-up within 1 week',
    (SELECT array_agg(0)::vector(1024) FROM generate_series(1, 1024)),
    'fhir_public',
    'emergency_medicine',
    '2024-01-01',
    1
),
(
    'FHIR ClinicalGuideline: Pediatric Dehydration',
    'SOURCE: FHIR R4 ClinicalGuideline resource — AAP Clinical Practice Guideline

SCOPE: Pediatric patients (0-18 years) presenting with dehydration from gastroenteritis, poor oral intake, or fluid losses.

DEHYDRATION SEVERITY ASSESSMENT:

Minimal/No Dehydration (< 3% weight loss):
- Mucous membranes moist, normal tears, normal skin turgor, normal mental status
- Urine output normal

Mild-Moderate Dehydration (3-9% weight loss):
- Mucous membranes slightly dry, decreased tears, tenting skin turgor (< 2 sec recoil)
- Tachycardia, normal BP, slightly prolonged capillary refill (2-3 sec)
- Decreased urine output, mildly irritable or restless

Severe Dehydration (>= 10% weight loss):
- Mucous membranes parched, absent tears, tenting skin turgor (> 2 sec recoil)
- Tachycardia, hypotension, markedly prolonged capillary refill (> 3 sec)
- Minimal or no urine output, lethargic or obtunded, sunken fontanelle (infants)

TRIAGE CRITERIA:
- ESI Level 1: Severe dehydration with shock (hypotension, altered mental status, poor perfusion), refractory hypoglycemia
- ESI Level 2: Severe dehydration (>= 10%), hemodynamic instability responsive to fluids, bloody diarrhea with dehydration, intractable vomiting with inability to maintain hydration, neonate with dehydration
- ESI Level 3: Mild-moderate dehydration (3-9%), failed oral rehydration therapy at home, persistent vomiting > 24 hours, concern for surgical abdomen
- ESI Level 4: Mild dehydration, tolerating sips, parent requesting evaluation, needs oral rehydration teaching
- ESI Level 5: No dehydration, diet counseling, follow-up visit

ORAL REHYDRATION THERAPY (ORT):
- Solution: WHO-ORS or commercial ORT (Pedialyte)
- Mild dehydration: 50 mL/kg over 4 hours + replacement of ongoing losses
- Moderate dehydration: 100 mL/kg over 4 hours + replacement of ongoing losses
- Administration: 5 mL q1-2 min by syringe, spoon, or cup. Increase volume as tolerated
- Ondansetron: 0.15 mg/kg (max 4mg) ODT to facilitate ORT if vomiting

IV FLUID PROTOCOL (for severe dehydration or ORT failure):
- Bolus: NS 20 mL/kg over 20 min, may repeat x3
- Maintenance: D5 NS at standard maintenance rate (4-2-1 rule: 4 mL/kg/hr for first 10kg, 2 mL/kg/hr for next 10kg, 1 mL/kg/hr thereafter)
- Deficit replacement: Remaining deficit over 24-48 hours
- Monitor: BMP for electrolyte derangements (hypo/hypernatremia), glucose q1-2h if < 5 years

REQUIRED DIAGNOSTICS:
- Level 1-2: BMP, CBC, glucose, blood gas, UA, blood culture if febrile and < 3 months
- Level 3: BMP (if moderate dehydration or IV fluids needed), glucose if < 2 years
- Level 4-5: Clinical assessment, consider fingerstick glucose in young infants

DISPOSITION:
- Severe dehydration: Admit for IV rehydration, cardiac monitoring if electrolyte abnormalities
- Moderate dehydration: ED observation 4-6 hours, reassess after ORT trial. Admit if ORT fails
- Mild dehydration: Discharge with ORT instructions, dietary guidance (BRAT diet), return precautions (no urine x 8h, persistent vomiting, blood in stool, lethargy)
- No dehydration: Discharge with anticipatory guidance',
    (SELECT array_agg(0)::vector(1024) FROM generate_series(1, 1024)),
    'fhir_public',
    'pediatrics',
    '2024-01-01',
    1
),
(
    'FHIR ClinicalGuideline: Acute Coronary Syndrome',
    'SOURCE: FHIR R4 ClinicalGuideline resource — AHA/ACC 2021 Chest Pain Guidelines

SCOPE: Adult patients presenting with suspected acute coronary syndrome (STEMI, NSTEMI, unstable angina).

ACS CLASSIFICATION:
- STEMI: ST-elevation in >= 2 contiguous leads (>= 1mm limb leads, >= 2mm precordial leads) or new LBBB with clinical suspicion
- NSTEMI: Troponin elevation above 99th percentile URL with ischemic symptoms or ECG changes (ST depression, T-wave inversion)
- Unstable Angina: Ischemic symptoms at rest or crescendo pattern, normal troponin, ECG may show transient ST changes

TRIAGE CRITERIA:
- ESI Level 1: STEMI (activate cath lab immediately), cardiogenic shock (SBP < 90, signs of hypoperfusion), cardiac arrest, ventricular arrhythmia (VT/VF)
- ESI Level 2: NSTEMI (troponin positive), ongoing ischemic chest pain unrelieved by nitroglycerin, dynamic ECG changes, HEART score >= 7, hemodynamically stable but high-risk features (Killip class II-III, new mitral regurgitation)
- ESI Level 3: Chest pain resolved, HEART score 4-6, awaiting serial troponins, known CAD with atypical symptoms
- ESI Level 4: Low-risk chest pain, HEART score 0-3, atypical features, age < 40 with no risk factors
- ESI Level 5: Non-cardiac chest pain clearly identified, musculoskeletal etiology, anxiety-related

STEMI MANAGEMENT (Door-to-Balloon < 90 minutes):
1. Activate cath lab immediately upon recognition
2. Aspirin 325mg (chew)
3. P2Y12 inhibitor: Ticagrelor 180mg or Clopidogrel 600mg loading dose
4. Heparin: UFH 60 units/kg bolus (max 4000 units)
5. Nitroglycerin 0.4mg SL q5min x3 (if SBP > 90, no RV infarction, no PDE5 inhibitor use < 48h)
6. Morphine: ONLY if pain refractory to nitrates (2-4mg IV)
7. Beta-blocker: Metoprolol 5mg IV if no contraindications (HR > 60, SBP > 100, no CHF, no AV block)

NSTEMI RISK STRATIFICATION (GRACE/TIMI scores):
- Very high risk (cath within 2h): Refractory angina, hemodynamic instability, VT/VF, acute heart failure
- High risk (cath within 24h): Troponin rise/fall, dynamic ST/T changes, GRACE > 140
- Intermediate risk (cath within 72h): Diabetes, CKD (GFR < 60), LVEF < 40%, prior PCI/CABG, GRACE 109-140
- Low risk: Normal troponins, no ECG changes, HEART 0-3

REQUIRED DIAGNOSTICS:
- Level 1: Stat ECG (repeat q15-30min if initial non-diagnostic), troponin stat, CBC, BMP, PT/INR, type and crossmatch, CXR (portable, do not delay cath lab)
- Level 2: ECG stat, troponin at 0h and 3h (high-sensitivity assay: 0h and 1h), CBC, BMP, BNP, lipid panel, CXR, echocardiogram if new murmur
- Level 3: ECG, serial troponins (0h, 3h, 6h), BMP, lipid panel
- Level 4-5: ECG, single troponin, clinical evaluation

DISPOSITION:
- STEMI: Cath lab -> CCU/ICU post-PCI
- NSTEMI very high/high risk: CCU or step-down, cardiology consult, plan for catheterization
- NSTEMI intermediate risk: Telemetry, non-invasive testing or cath within 72h
- Unstable angina / low risk: Observation unit, stress testing, discharge with cardiology follow-up if negative
- Non-cardiac: Discharge with PCP follow-up',
    (SELECT array_agg(0)::vector(1024) FROM generate_series(1, 1024)),
    'fhir_public',
    'cardiology',
    '2024-01-01',
    1
)
ON CONFLICT DO NOTHING;
