/*
 * This query returns a list of all curator comments on genes and gene products
 */
SELECT
    feature2.uniquename AS gene_id,
	feature1.uniquename AS transcript_id,
	featureprop.value AS curator_comment
FROM
    featureprop                                                                     -- start off with a gene product (e.g. polypeptide)
	JOIN
	feature_relationship relation1 ON featureprop.feature_id = relation1.subject_id	-- connect gene product...
	JOIN
	feature feature1 ON relation1.object_id = feature1.feature_id					-- ... with transcript from which it derives
	JOIN
	feature_relationship relation2 ON relation2.subject_id = feature1.feature_id	-- connect transcript...
	JOIN
	feature feature2 ON relation2.object_id = feature2.feature_id					-- ... with the corresponding gene
	JOIN
	organism ON feature2.organism_id = organism.organism_id                         -- finally connect with the organism
WHERE
	featureprop.type_id IN (SELECT cvterm_id FROM cvterm WHERE name IN ('comment', 'curation'))  -- restrict to curator comments
	AND
	feature2.type_id IN (SELECT cvterm_id FROM cvterm WHERE name IN ('gene', 'pseudogene'))  -- restrict to feature types
	AND
	relation1.type_id IN (SELECT cvterm_id FROM cvterm WHERE name = 'derives_from')	-- gene product 'derives from' transcript
	AND
	relation2.type_id IN (SELECT cvterm_id FROM cvterm WHERE name = 'part_of')	    -- transcript is 'part of' gene, at least in the Sanger pathogen DBs
	AND
	:ORGANISM_CONDITION                                                             -- a specific organism, or all
	AND
	feature2.is_obsolete = 'f'														-- ignore obsolete features
ORDER BY
	gene_id,
	transcript_id,
	curator_comment
