-- patch.sql
--
-- Move payment 8678 (Don Palmer, $98.80, 2026-01-09) from the passenger
-- side of flight 25191 to the pilot side of flight 25199.
--
-- Background:
--   Don intended to finalise/pay for his own flight 25199 (he was pilot,
--   Passenger Flight type, no passenger). Instead he hit "submit" on
--   flight 25191 (where he was logged as Greg Shooter's passenger), so
--   the Stripe charge was wired in as 25191.pay_id2 / basis2 / amount2.
--   Flight 25199's payment_info still reads {"basis":"-","pay_id":0,...}
--   so the reminder cron keeps emailing him.
--
-- Before:
--   25191.payment_info = {basis:"First hour free…",amount:82,pay_id:8652,
--                         basis2:"Launch+time - $82+$16.8 = $98.8",
--                         amount2:98.8,pay_id2:8678,paidBy:[129,106]}
--   25199.payment_info = {basis:"-",amount:0,pay_id:0,paidBy:[106]}
--   payments.id=8678 notes = "Payment for Flights (25191) Tok ch_…"
--
-- After:
--   25191.payment_info = {basis:"First hour free…",amount:82,pay_id:8652,
--                         paidBy:[129,106]}    -- passenger side cleared
--   25199.payment_info = {basis:"Launch+time - $82+$16.8 = $98.8",
--                         amount:98.8,pay_id:8678,paidBy:[106]}
--   payments.id=8678 notes = "Payment for Flights (25199) Tok ch_…"

START TRANSACTION;

-- 1. Strip passenger-side payment fields from flight 25191
UPDATE flights
SET payment_info = JSON_REMOVE(
        JSON_REMOVE(
            JSON_REMOVE(payment_info, '$.pay_id2'),
            '$.amount2'),
        '$.basis2')
WHERE id = 25191;

-- 2. Write the pilot-side payment onto flight 25199
UPDATE flights
SET payment_info = JSON_OBJECT(
        'basis',  'Launch+time - $82+$16.8 = $98.8',
        'amount', 98.8,
        'pay_id', 8678,
        'paidBy', JSON_ARRAY(106))
WHERE id = 25199;

-- 3. Re-label payment 8678 to reference the correct flight
UPDATE payments
SET notes = REPLACE(notes, 'Flights (25191)', 'Flights (25199)')
WHERE id = 8678;

COMMIT;
