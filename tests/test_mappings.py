from utils.mappings import classify_wholesaler, ndc_to_product, normalize_ndc


def test_normalize_clean_ndc():
    assert normalize_ndc("66794024942") == "66794024942"


def test_normalize_float_ndc():
    assert normalize_ndc(66794024942.0) == "66794024942"


def test_normalize_non_numeric_returns_none():
    assert normalize_ndc("PIR030") is None


def test_unmapped_ndc_bucket():
    assert ndc_to_product("99999999999") == "UNMAPPED"
    assert ndc_to_product("PIR030") == "UNMAPPED"


def test_known_ndc():
    assert ndc_to_product("66794001525") == "SEVOFLURANE"
    assert ndc_to_product(66794001525.0) == "SEVOFLURANE"


def test_classify_wholesaler():
    assert classify_wholesaler("CENCORA GLOBAL PROCUREMEN") == "ABC"
    assert classify_wholesaler("McKesson Medical Surgical") == "Mckesson Medical"
    assert classify_wholesaler("McKesson Corp") == "Mckesson"
    assert classify_wholesaler("Cardinal Health") == "Cardinal"
    assert classify_wholesaler("Random Dist") == "Others"
