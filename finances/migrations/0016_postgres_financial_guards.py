from django.db import migrations


FORWARD_SQL = """
CREATE OR REPLACE FUNCTION yelen_guard_paiement_immutable()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'Un paiement comptabilisé est immuable et ne peut pas être supprimé.'
        USING ERRCODE = '55000';
END;
$$;

DROP TRIGGER IF EXISTS yelen_paiement_immutable ON finances_paiement;
CREATE TRIGGER yelen_paiement_immutable
BEFORE UPDATE OR DELETE ON finances_paiement
FOR EACH ROW
EXECUTE FUNCTION yelen_guard_paiement_immutable();

CREATE OR REPLACE FUNCTION yelen_guard_remboursement()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    payment_amount numeric;
    already_refunded numeric;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Un remboursement ne peut pas être supprimé.'
            USING ERRCODE = '55000';
    END IF;

    IF TG_OP = 'UPDATE' THEN
        IF OLD.paiement_id IS DISTINCT FROM NEW.paiement_id
           OR OLD.montant IS DISTINCT FROM NEW.montant
           OR OLD.motif IS DISTINCT FROM NEW.motif
           OR OLD.date_remboursement IS DISTINCT FROM NEW.date_remboursement
           OR OLD.rembourse_par_id IS DISTINCT FROM NEW.rembourse_par_id
           OR OLD.created_at IS DISTINCT FROM NEW.created_at
           OR OLD.created_by_id IS DISTINCT FROM NEW.created_by_id
           OR (OLD.is_active IS FALSE AND NEW.is_active IS DISTINCT FROM FALSE)
        THEN
            RAISE EXCEPTION 'Un remboursement existant est immuable ; seule son annulation auditée est permise.'
                USING ERRCODE = '55000';
        END IF;

        IF OLD.is_active IS TRUE AND NEW.is_active IS FALSE
           AND NULLIF(trim(current_setting('yelen.refund_cancel_reason', true)), '') IS NULL
        THEN
            RAISE EXCEPTION 'L''annulation d''un remboursement exige un motif audité.'
                USING ERRCODE = '55000';
        END IF;
        RETURN NEW;
    END IF;

    SELECT montant
      INTO payment_amount
      FROM finances_paiement
     WHERE id = NEW.paiement_id
     FOR UPDATE;

    IF payment_amount IS NULL THEN
        RAISE EXCEPTION 'Le paiement d''origine est introuvable.'
            USING ERRCODE = '55000';
    END IF;

    SELECT COALESCE(SUM(montant), 0)
      INTO already_refunded
      FROM finances_remboursement
     WHERE paiement_id = NEW.paiement_id
       AND is_active IS TRUE;

    IF already_refunded + NEW.montant > payment_amount THEN
        RAISE EXCEPTION 'Le total des remboursements ne peut pas dépasser le paiement.'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS yelen_remboursement_guard ON finances_remboursement;
CREATE TRIGGER yelen_remboursement_guard
BEFORE INSERT OR UPDATE OR DELETE ON finances_remboursement
FOR EACH ROW
EXECUTE FUNCTION yelen_guard_remboursement();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS yelen_remboursement_guard ON finances_remboursement;
DROP FUNCTION IF EXISTS yelen_guard_remboursement();
DROP TRIGGER IF EXISTS yelen_paiement_immutable ON finances_paiement;
DROP FUNCTION IF EXISTS yelen_guard_paiement_immutable();
"""


class Migration(migrations.Migration):
    dependencies = [
        ('finances', '0015_bourseeleve_bourse_montant_positif_and_more'),
    ]

    operations = [
        migrations.RunSQL(FORWARD_SQL, REVERSE_SQL),
    ]
