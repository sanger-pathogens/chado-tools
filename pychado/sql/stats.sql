/*
 * This query returns all changes in annotation since a specified date
 */
SELECT
    organism.abbreviation AS organism_name,
	feature1.uniquename AS transcript_id,
	feature2.uniquename AS gene_id,
	property2.value AS "date",
	property1.value AS annotation
FROM
	feature_cvterm fcvt																-- start off with a gene product (e.g. polypeptide)
	JOIN
	cvterm cvt USING (cvterm_id)
	JOIN
	"cv" USING (cv_id)
	JOIN
	feature_cvtermprop property1 USING (feature_cvterm_id)							-- first property of the gene product
	JOIN
	feature_cvtermprop property2 USING (feature_cvterm_id)							-- second property of the gene product
	JOIN
	feature_relationship relation1 ON fcvt.feature_id = relation1.subject_id		-- connect gene product...
	JOIN
	feature feature1 ON relation1.object_id = feature1.feature_id					-- ... with transcript from which it derives
	JOIN
	feature_relationship relation2 ON relation2.subject_id = feature1.feature_id	-- connect transcript...
	JOIN
	feature feature2 ON relation2.object_id = feature2.feature_id					-- ... with the corresponding gene
	JOIN
	organism ON feature2.organism_id = organism.organism_id                         -- finally connect with the organism
WHERE
	cv.name = 'annotation_change'		                                            -- capture all changes in annotation
	AND
	property1.type_id IN (SELECT cvterm_id FROM cvterm WHERE name = 'qualifier')	-- restrict to actual annotation descriptions
	AND
	property1.value != ''
	AND
	property2.type_id IN (SELECT cvterm_id FROM cvterm WHERE name = 'date')			-- restrict to certain dates
	AND
	property2.value >= :start_date
	AND
	property2.value <= :end_date
	AND
	relation1.type_id IN (SELECT cvterm_id FROM cvterm WHERE name = 'derives_from')	-- gene product 'derives from' transcript
	AND
	relation2.type_id IN (SELECT cvterm_id FROM cvterm WHERE name = 'part_of')	    -- transcript is 'part of' gene, at least in the Sanger pathogen DBs
	AND
	:ORGANISM_CONDITION                                                             -- a specific organism, or all
ORDER BY
	organism_name,
	transcript_id,
	"date",
	annotation
