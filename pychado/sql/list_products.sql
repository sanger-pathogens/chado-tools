/*
 * This query returns a list of all GeneDB products of transcripts
 */
SELECT
	feature1.uniquename AS mrnaid,
	feature2.uniquename AS geneid,
	feature2.name AS genename,
	cvt.name AS product,
	fcvt.rank AS rankalternative,
	feature1.organism_id AS organismid
FROM
	feature_cvterm fcvt																-- start off with a gene product (e.g. polypeptide)
	JOIN
	cvterm cvt USING (cvterm_id)
	JOIN
	feature_relationship relation1 ON fcvt.feature_id = relation1.subject_id		-- connect gene product...
	JOIN
	feature feature1 ON relation1.object_id = feature1.feature_id					-- ... with transcript from which it derives
	JOIN
	feature_relationship relation2 ON relation2.subject_id = feature1.feature_id	-- connect transcript...
	JOIN
	feature feature2 ON relation2.object_id = feature2.feature_id					-- ... with the corresponding gene
WHERE
	cvt.cvterm_id IN (SELECT cvterm_id FROM cvterm JOIN cv USING (cv_id) WHERE cv.name = 'genedb_products') -- restrict to GeneDB products
	AND
	feature1.organism_id IN (SELECT organism_id FROM organism WHERE {{CONDITION}})	-- a specific organism
	AND
	relation1.type_id IN (SELECT cvterm_id FROM cvterm WHERE name = 'derives_from')	-- gene product 'derives from' transcript
	AND
	feature1.is_obsolete = 'f'														-- ignore obsolete features
ORDER BY
	mrnaid,
	organismid,
	rankalternative,
	product
