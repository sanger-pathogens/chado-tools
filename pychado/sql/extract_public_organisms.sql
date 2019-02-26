SELECT
    o.abbreviation,
    o.genus,
    o.species,
    o.infraspecific_name AS strain,
    o.common_name,
    op1.value AS version,
    op2.value AS taxon_id,
    d.accession AS wikidata_id
FROM
    organism o
    LEFT JOIN (
        organism_dbxref od
        JOIN
        dbxref d ON d.dbxref_id = od.dbxref_id
        JOIN
        db ON (db.db_id = d.db_id AND db.name = 'Wikidata')
    ) ON od.organism_id = o.organism_id
    LEFT JOIN (
        organismprop op1
        JOIN
        cvterm c1 ON (op1.type_id = c1.cvterm_id AND c1.name = 'version')
    ) ON op1.organism_id = o.organism_id
    LEFT JOIN (
        organismprop op2
        JOIN
        cvterm c2 ON (op2.type_id = c2.cvterm_id AND c2.name = 'taxonId')
    ) ON op2.organism_id = o.organism_id
    JOIN (
        organismprop op3
        JOIN
        cvterm c3 ON (op3.type_id = c3.cvterm_id AND c3.name = 'genedb_public')
    ) ON op3.organism_id = o.organism_id
WHERE
    o.abbreviation != 'dummy'
ORDER BY
    genus,
    species,
    strain
