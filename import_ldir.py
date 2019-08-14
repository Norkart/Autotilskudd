
import ogr, osr
import psycopg2

wgs84 = osr.SpatialReference()
wgs84.ImportFromEPSG(4326)

def print_layer_def(layer):
    layerDefinition = layer.GetLayerDefn()

    for i in range(layerDefinition.GetFieldCount()):
        fieldName = layerDefinition.GetFieldDefn(i).GetName()
        fieldTypeCode = layerDefinition.GetFieldDefn(i).GetType()
        fieldType = layerDefinition.GetFieldDefn(i).GetFieldTypeName(fieldTypeCode)
        fieldWidth = layerDefinition.GetFieldDefn(i).GetWidth()
        GetPrecision = layerDefinition.GetFieldDefn(i).GetPrecision()

        print(fieldName + " - " + fieldType + " " + str(fieldWidth) + " " + str(GetPrecision))

def import_pt(layer, cur, default_prod=None):
    # print_layer_def(layer)

    # Find layer definitions
    layerDefinition = layer.GetLayerDefn()

    # Fra PT
    artype_idx = layerDefinition.GetFieldIndex("arealtype")
    grunnf_idx = layerDefinition.GetFieldIndex("grunnforho")

    # Fra RMP
    soknad_id_idx = layerDefinition.GetFieldIndex("SOKNAD_ID")
    soknads_om_idx = layerDefinition.GetFieldIndex("SOKNADS_OM")
    godkjent_s_idx = layerDefinition.GetFieldIndex("GODKJENT_S")
    commit_dat_idx = layerDefinition.GetFieldIndex("COMMIT_DAT")
    tiltak_nav_idx = layerDefinition.GetFieldIndex("TILTAK_NAV")
    satskode_idx = layerDefinition.GetFieldIndex("SATSKODE")
    sid_idx = layerDefinition.GetFieldIndex("SID")
    rmp_fnr_idx = layerDefinition.GetFieldIndex("Fnr")

    # Generelt
    knr_idx = layerDefinition.GetFieldIndex("MATRIKKELK")
    if knr_idx == -1:
        knr_idx = layerDefinition.GetFieldIndex("HKOMNR")

    gnr_idx = layerDefinition.GetFieldIndex("GNR")
    if gnr_idx == -1:
        gnr_idx = layerDefinition.GetFieldIndex("HGNR")

    bnr_idx = layerDefinition.GetFieldIndex("BNR")
    if bnr_idx == -1:
        bnr_idx = layerDefinition.GetFieldIndex("HBNR")

    fnr_idx = layerDefinition.GetFieldIndex("FNR")
    if fnr_idx == -1:
        fnr_idx = layerDefinition.GetFieldIndex("HFNR")

    snr_idx = layerDefinition.GetFieldIndex("SNR")
    prod_idx = layerDefinition.GetFieldIndex("Prod")
    dp_fra_idx = layerDefinition.GetFieldIndex("DP_fra")
    dp_til_idx = layerDefinition.GetFieldIndex("DP_til")


    # Read layer
    for feature in layer:
        # PT layer specific data
        artype = feature[artype_idx] if artype_idx != -1 else None
        argrunnf = feature[grunnf_idx] if grunnf_idx != -1 else None

        # RMP layer specific data
        soknad_id = feature[soknad_id_idx] if soknad_id_idx != -1 else None
        soknads_om = feature[soknads_om_idx] if soknads_om_idx != -1 else None
        godkjent_s = feature[godkjent_s_idx] if godkjent_s_idx != -1 else None
        commit_dat = feature[commit_dat_idx] if commit_dat_idx != -1 else None
        tiltak_nav = feature[tiltak_nav_idx] if tiltak_nav_idx != -1 else None
        satskode = feature[satskode_idx] if satskode_idx != -1 else None
        sid = feature[sid_idx] if sid_idx != -1 else None
        rmp_fnr = feature[rmp_fnr_idx] if rmp_fnr_idx != -1 else None

        # General data
        knr = feature[knr_idx] if knr_idx != -1 else None
        gnr = feature[gnr_idx] if gnr_idx != -1 else None
        bnr = feature[bnr_idx] if bnr_idx != -1 else None
        fnr = feature[fnr_idx] if fnr_idx != -1 else None
        snr = feature[snr_idx] if snr_idx != -1 else None
        prod = feature[prod_idx] if prod_idx != -1 else None
        dp_fra = feature[dp_fra_idx] if dp_fra_idx != -1 else None
        dp_til = feature[dp_til_idx] if dp_til_idx != -1 else None

        # Geometric object
        geog = feature.GetGeometryRef()
        geog.TransformTo(wgs84)
        geog_wkb = geog.ExportToWkb()

        # If no product found, fallback to default
        if not prod:
            prod = default_prod

        # Insert common data into database
        cur.execute("""INSERT INTO pa (knr, gnr, bnr, snr, fnr, prod, dp_fra, dp_til, geog) 
                       VALUES ( %s, %s, %s, %s, %s, %s, %s, %s, ST_GeomFromWKB(%s)::geography ) 
                       RETURNING id;""",
                    (knr, gnr, bnr, snr, fnr, prod, dp_fra, dp_til, geog_wkb))
        # Extract id of inserted row
        res = cur.fetchall()
        id = res[0][0]

        # Insert PT data
        if id and (artype or argrunnf):
            cur.execute("""INSERT INTO pt (id, artype, argrunnf)
                            VALUES (%s, %s, %s);""",
                        (id, artype, argrunnf))

        # Insert RMP data
        if id and (soknad_id or soknads_om or godkjent_s or commit_dat or tiltak_nav or satskode or sid or rmp_fnr):
            cur.execute("""INSERT INTO rmp (id, soknad_id, soknads_om, godkjent_s, commit_dat, tiltak_nav, satskode, sid, fnr)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                        (id, soknad_id, soknads_om, godkjent_s, commit_dat, tiltak_nav, satskode, sid, rmp_fnr))


def main():
    with psycopg2.connect("host=beistet port=5433 dbname=LDir user=postgres password=1234") as conn:

        # ['Gras_fra_RMP', 'Korn_fra_RMP', 'Gras_fra_PT', 'Korn_fra_PT']
        filename = r"C:/Users/runaas.NORKART/PycharmProjects/SentinelTest/data/POC_KornGras.gdb/POC_KornGras.gdb"

        ds = ogr.Open(filename)
        with conn.cursor() as cur:
            import_pt(ds.GetLayerByName('Gras_fra_PT'), cur, default_prod="Gras")
            import_pt(ds.GetLayerByName('Korn_fra_PT'), cur, default_prod="Korn")
            import_pt(ds.GetLayerByName('Gras_fra_RMP'), cur, default_prod="Gras")
            import_pt(ds.GetLayerByName('Korn_fra_RMP'), cur, default_prod="Korn")

if __name__ == '__main__':
    main()