SELECT
    cvterm.name AS name,
    cvterm.definition AS definition,
    cvterm.is_obsolete,
    cvterm.is_relationshiptype,
    cv.name AS vocabulary,
    db.name AS xref_database,
    dbxref.accession AS xref_accession,
    dbxref.version AS xref_version
FROM
    cvterm
    JOIN
    "cv" USING (cv_id)
    JOIN
    dbxref USING (dbxref_id)
    JOIN
    db USING (db_id)
WHERE
    :CV_CONDITION
    AND
    :DB_CONDITION
ORDER BY cvterm_id ASC
