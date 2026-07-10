<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:math="http://www.w3.org/2005/xpath-functions/math"
    xmlns:xpf="http://www.w3.org/2005/xpath-functions" xmlns:mods="http://www.loc.gov/mods/v3" xmlns:mods2la="https://linked.art/ns/v1/linked-art.json"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#" xmlns:xsd="http://www.w3.org/2001/XMLSchema#"
    xmlns:crm="http://www.cidoc-crm.org/cidoc-crm/" xmlns:la="https://linked.art/ns/terms/" xmlns:dig="http://www.ics.forth.gr/isl/CRMdig/"
    xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" exclude-result-prefixes="xsl xs math xpf mods mods2la" version="3.0">

    <xsl:output method="xml" encoding="UTF-8" indent="yes"/>

    <xsl:variable name="manifestBaseURL">https://s3.us-east-1.amazonaws.com/iiif-manifest-cache-production/pid-</xsl:variable>

    <xsl:variable name="resolver-url">http://127.0.0.1:8001/</xsl:variable>

    <xsl:variable name="resolver-on" as="xs:boolean">
        <xsl:value-of select="unparsed-text-available($resolver-url)"/>
    </xsl:variable>

    <xsl:variable name="roles" as="node()*">
        <xsl:copy-of select="document('roles.xml')"/>
    </xsl:variable>

    <xsl:template match="/">
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#" xmlns:xsd="http://www.w3.org/2001/XMLSchema#"
            xmlns:crm="http://www.cidoc-crm.org/cidoc-crm/">
            <xsl:apply-templates select="//mods:mods"/>
        </rdf:RDF>
    </xsl:template>

    <xsl:template match="mods:mods">
        <xsl:variable name="id" select="mods:recordInfo/mods:recordIdentifier[@source = 'SIRSI']"/>
        <xsl:variable name="pid" select="mods:recordInfo/mods:recordIdentifier[@source = 'PID']"/>
        
        <crm:E22_Human-Made_Object>
            <xsl:attribute name="rdf:about" select="concat('https://search.lib.virginia.edu/sources/images/items/', $id)"/>
            <rdfs:label>
                <xsl:value-of select="mods2la:generateTitle(mods:titleInfo)"/>
            </rdfs:label>

            <!-- title -->
            <crm:P1_is_identified_by>
                <crm:E33_E41_Linguistic_Appellation>
                    <crm:P190_has_symbolic_content>
                        <xsl:value-of select="mods2la:generateTitle(mods:titleInfo)"/>
                    </crm:P190_has_symbolic_content>
                    <crm:P2_has_type rdf:resource="http://vocab.getty.edu/aat/300404670"/>
                </crm:E33_E41_Linguistic_Appellation>
            </crm:P1_is_identified_by>

            <!-- useful identifiers -->
            <xsl:apply-templates select="mods:identifier[@type = 'local']"/>

            <!-- HMO classification -->
            <xsl:apply-templates select="mods:typeOfResource[@valueURI]"/>
            <xsl:apply-templates select="mods:genre[@authority and @valueURI]"/>

            <!-- production event -->
            <xsl:if test="mods:name or mods:relatedItem[@type = 'original']/mods:originInfo or mods:originInfo">
                <crm:P108i_was_produced_by>
                    <crm:E12_Production>
                        <!-- accommodate differing originInfo, depending on MARC source or manual MODS -->
                        <xsl:choose>
                            <xsl:when test="mods:relatedItem[@type = 'original']/mods:originInfo">
                                <xsl:apply-templates select="mods:relatedItem[@type = 'original']/mods:originInfo[1]"/>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:apply-templates select="mods:originInfo[1]"/>
                            </xsl:otherwise>
                        </xsl:choose>

                        <xsl:variable name="productionHasParts" as="xs:boolean">
                            <xsl:choose>
                                <xsl:when test="count(distinct-values(mods:name/mods:role/mods:roleTerm[@authority = 'marcrelator']/@valueURI)) &gt; 1 and count(mods:name) &gt; 1">
                                    <xsl:value-of select="true()"/>
                                </xsl:when>
                                <xsl:when test="mods:name/mods:role/mods:roleTerm[@authority = 'marcrelator' and @valueURI] and mods:name[not(mods:role)]">
                                    <xsl:value-of select="true()"/>
                                </xsl:when>
                                <xsl:otherwise>
                                    <xsl:value-of select="false()"/>
                                </xsl:otherwise>
                            </xsl:choose>

                        </xsl:variable>

                        <xsl:choose>
                            <xsl:when test="$productionHasParts = true()">
                                <xsl:for-each select="mods:name[@valueURI]">
                                    <crm:P9_consists_of>
                                        <crm:E12_Production>
                                            <xsl:variable name="property">
                                                <xsl:choose>
                                                    <xsl:when test="mods:role/mods:roleTerm[@authority = 'marcrelator' and @valueURI]">
                                                        <xsl:variable name="uri" select="mods:role/mods:roleTerm[@authority = 'marcrelator' and @valueURI][1]/@valueURI"/>

                                                        <xsl:value-of select="$roles//role[@marcrelator = $uri]/@property"/>
                                                    </xsl:when>
                                                    <xsl:otherwise>
                                                        <xsl:text>carried_out_by</xsl:text>
                                                    </xsl:otherwise>
                                                </xsl:choose>
                                            </xsl:variable>

                                            <xsl:element name="crm:{if ($property = 'carried_out_by') then 'P14_carried_out_by' else 'P15_was_influenced_by'}"
                                                namespace="http://www.cidoc-crm.org/cidoc-crm/">
                                                <xsl:attribute name="rdf:resource" select="@valueURI"/>
                                            </xsl:element>

                                            <xsl:for-each select="mods:role/mods:roleTerm[@authority = 'marcrelator' and @valueURI]">
                                                <xsl:variable name="uri" select="@valueURI"/>

                                                <crm:P32_used_general_technique>
                                                    <xsl:attribute name="rdf:resource" select="
                                                            if ($roles//role[@marcrelator = $uri]/@technique) then
                                                                $roles//role[@marcrelator = $uri]/@technique
                                                            else
                                                                $uri"/>

                                                </crm:P32_used_general_technique>
                                            </xsl:for-each>
                                        </crm:E12_Production>
                                    </crm:P9_consists_of>
                                </xsl:for-each>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:for-each select="mods:name[@valueURI]">
                                    <xsl:variable name="property">
                                        <xsl:choose>
                                            <xsl:when test="mods:role/mods:roleTerm[@authority = 'marcrelator' and @valueURI]">
                                                <xsl:variable name="uri" select="mods:role/mods:roleTerm[@authority = 'marcrelator' and @valueURI][1]/@valueURI"/>

                                                <xsl:value-of select="$roles//role[@marcrelator = $uri]/@property"/>
                                            </xsl:when>
                                            <xsl:otherwise>
                                                <xsl:text>carried_out_by</xsl:text>
                                            </xsl:otherwise>
                                        </xsl:choose>
                                    </xsl:variable>

                                    <xsl:if test="not($property = 'provenance')">
                                        <xsl:element name="crm:{if ($property = 'carried_out_by') then 'P14_carried_out_by' else 'P15_was_influenced_by'}"
                                            namespace="http://www.cidoc-crm.org/cidoc-crm/">
                                            <xsl:attribute name="rdf:resource" select="@valueURI"/>
                                        </xsl:element>

                                        <xsl:for-each select="distinct-values(mods:name/mods:role/mods:roleTerm[@authority = 'marcrelator']/@valueURI)">
                                            <xsl:variable name="uri" select="."/>

                                            <crm:P32_used_general_technique>
                                                <xsl:attribute name="rdf:resource" select="
                                                        if ($roles//role[@marcrelator = $uri]/@technique) then
                                                            $roles//role[@marcrelator = $uri]/@technique
                                                        else
                                                            $uri"/>
                                            </crm:P32_used_general_technique>
                                        </xsl:for-each>
                                    </xsl:if>
                                </xsl:for-each>
                            </xsl:otherwise>
                        </xsl:choose>
                    </crm:E12_Production>
                </crm:P108i_was_produced_by>
            </xsl:if>

            <!-- physical description -->
            <xsl:apply-templates select="mods:physicalDescription"/>

            <!-- General subject terms/aboutness, use mods:form conditional -->
            <!-- a mods:subject with child level URIs will have individually addressable parts -->
            <xsl:apply-templates select="mods:subject[@authority = 'lcsh' and child::*[@valueURI]] | mods:subject[@authority = 'lcnaf' and child::*[@valueURI]]"/>
            <xsl:apply-templates
                select="mods:subject/mods:hierarchicalGeographic/*[starts-with(@valueURI, 'https://sws.geonames.org/') or starts-with(@valueURI, 'http://vocab.getty.edu/tgn/')]"/>

            <!-- VisualItems depicted or represented in image: rewrite based on mods:form conditional -->
            <xsl:apply-templates select="mods:subject[@valueURI and not(@authority)][mods:topic]"/>
            <xsl:apply-templates select="mods:subject[@valueURI and @authority = 'lcsh'][mods:topic]"/>

            <!-- textual statements -->
            <xsl:apply-templates select="mods:abstract"/>
            <xsl:apply-templates select="mods:physicalDescription/mods:extent" mode="statement"/>

            <!-- collection -->
            <xsl:if test="mods:relatedItem[@type = 'host' and lower-case(@displayLabel) = 'part of'][mods:location/mods:url]">
                <xsl:apply-templates select="mods:relatedItem[@type = 'host' and lower-case(@displayLabel) = 'part of'][mods:location/mods:url]"/>
            </xsl:if>

            <xsl:if test="string($pid)">
                <crm:P129i_is_subject_of>
                    <crm:E33_Linguistic_Object>
                        <la:digitally_carried_by>
                            <dig:D1_Digital_Object>
                                <la:access_point rdf:resource="{concat($manifestBaseURL, replace($pid, ':', '-'))}"/>
                                <dc:format>application/ld+json;profile='http://iiif.io/api/presentation/3/context.json'</dc:format>
                                <dcterms:conformsTo rdf:resource="http://iiif.io/api/presentation"/>
                            </dig:D1_Digital_Object>
                        </la:digitally_carried_by>
                    </crm:E33_Linguistic_Object>
                </crm:P129i_is_subject_of>
            </xsl:if>

        </crm:E22_Human-Made_Object>
        <!-- end of HMO -->
    </xsl:template>

    <xsl:template match="mods:identifier[@type = 'local']">
        <xsl:if test="contains(lower-case(@displayLabel), 'call number')">

            <crm:P1_is_identified_by>
                <crm:E33_E41_Linguistic_Appellation>
                    <crm:P190_has_symbolic_content>
                        <xsl:value-of select="."/>
                    </crm:P190_has_symbolic_content>
                    <crm:P2_has_type rdf:resource="http://vocab.getty.edu/aat/300311706"/>
                </crm:E33_E41_Linguistic_Appellation>
            </crm:P1_is_identified_by>
        </xsl:if>
    </xsl:template>

    <!-- classifications -->
    <xsl:template match="mods:typeOfResource[@valueURI] | mods:genre[@valueURI]">
        <crm:P2_has_type rdf:resource="{@valueURI}"/>
    </xsl:template>

    <xsl:template match="mods:abstract">
        <crm:P67i_is_referred_to_by>
            <crm:E33_Linguistic_Object>
                <crm:P190_has_symbolic_content>
                    <xsl:value-of select="."/>
                </crm:P190_has_symbolic_content>
                <crm:P2_has_type rdf:resource="http://vocab.getty.edu/aat/300435416"/>
            </crm:E33_Linguistic_Object>
        </crm:P67i_is_referred_to_by>
    </xsl:template>

    <!-- production properties -->
    <xsl:template match="mods:originInfo">

        <!-- dates -->
        <xsl:if test="mods:dateCreated or mods:dateIssued">
            <xsl:call-template name="timespan"/>
        </xsl:if>

        <xsl:apply-templates select="mods:place/mods:placeTerm[@valueURI]" mode="production"/>
    </xsl:template>

    <xsl:template name="timespan">
        <xsl:variable name="value">
            <xsl:choose>
                <xsl:when test="mods:dateCreated[@point = 'start'] and mods:dateCreated[@point = 'end']">
                    <xsl:choose>
                        <xsl:when test="mods:dateCreated[@point = 'start' and @encoding = 'iso8601'] and mods:dateCreated[@point = 'end' and @encoding = 'iso8601']">
                            <xsl:value-of
                                select="concat(mods:dateCreated[@point = 'start' and @encoding = 'iso8601'], '/', mods:dateCreated[@point = 'end' and @encoding = 'iso8601'])"/>
                        </xsl:when>
                        <xsl:otherwise>
                            <xsl:value-of select="concat(mods:dateCreated[@point = 'start'], '/', mods:dateCreated[@point = 'end'])"/>
                        </xsl:otherwise>
                    </xsl:choose>
                </xsl:when>
                <xsl:when test="mods:dateIssued[@point = 'start'] and mods:dateIssued[@point = 'end']">
                    <xsl:choose>
                        <xsl:when test="mods:dateIssued[@point = 'start' and @encoding = 'iso8601'] and mods:dateIssued[@point = 'end' and @encoding = 'iso8601']">
                            <xsl:value-of
                                select="concat(mods:dateIssued[@point = 'start' and @encoding = 'iso8601'], '/', mods:dateIssued[@point = 'end' and @encoding = 'iso8601'])"/>
                        </xsl:when>
                        <xsl:otherwise>
                            <xsl:value-of select="concat(mods:dateIssued[@point = 'start'], '/', mods:dateIssued[@point = 'end'])"/>
                        </xsl:otherwise>
                    </xsl:choose>
                </xsl:when>
                <xsl:when test="mods:dateCreated[(@encoding = 'iso8601' or @encoding = 'edtf') and not(@point)]">
                    <xsl:value-of select="mods:dateCreated[@encoding = 'iso8601' or @encoding = 'edtf'][1]"/>
                </xsl:when>
                <xsl:when test="mods:dateIssued[@encoding = 'iso8601' or @encoding = 'edtf' and not(@point)]">
                    <xsl:value-of select="mods:dateIssued[@encoding = 'iso8601' or @encoding = 'edtf'][1]"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:choose>
                        <xsl:when test="mods:dateCreated">
                            <xsl:value-of select="mods:dateCreated[1]"/>
                        </xsl:when>
                        <xsl:when test="mods:dateIssued">
                            <xsl:value-of select="mods:dateIssued[1]"/>
                        </xsl:when>
                    </xsl:choose>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:variable>

        <xsl:if test="string($value)">
            <crm:P4_has_time-span>
                <crm:E52_Time-Span>
                    <rdfs:label>
                        <xsl:value-of select="$value"/>
                    </rdfs:label>

                    <xsl:variable name="dateRange" as="node()*">
                        <xsl:if test="$resolver-on">
                            <result>
                                <xsl:if test="unparsed-text-available(concat($resolver-url, 'parse?date=', encode-for-uri($value)))">
                                    <xsl:copy-of select="json-to-xml(unparsed-text(concat($resolver-url, 'parse?date=', encode-for-uri($value))))"/>
                                </xsl:if>
                            </result>
                        </xsl:if>
                    </xsl:variable>

                    <xsl:if test="$dateRange//xpf:string[@key = 'fromDate'] and $dateRange//xpf:string[@key = 'toDate']">
                        <crm:P82a_begin_of_the_begin rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">
                            <xsl:value-of select="concat($dateRange//xpf:string[@key = 'fromDate'], 'T00:00:00Z')"/>
                        </crm:P82a_begin_of_the_begin>
                        <crm:P82b_end_of_the_end rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">
                            <xsl:value-of select="concat($dateRange//xpf:string[@key = 'toDate'], 'T23:59:59Z')"/>
                        </crm:P82b_end_of_the_end>
                    </xsl:if>
                </crm:E52_Time-Span>
            </crm:P4_has_time-span>

        </xsl:if>
    </xsl:template>

    <xsl:template match="mods:placeTerm" mode="production">
        <crm:P7_took_place_at rdf:resource="{@valueURI}"/>
    </xsl:template>

    <!-- VisualItem 'shows' -->
    <xsl:template match="mods:subject[@valueURI and not(@authority)][mods:topic]">
        <crm:P65_shows_visual_item>
            <crm:E36_Visual_Item>
                <crm:P199_represents_instance_of_type rdf:resource="{@valueURI}"/>
            </crm:E36_Visual_Item>
        </crm:P65_shows_visual_item>
    </xsl:template>

    <xsl:template match="mods:subject[@valueURI and @authority = 'lcsh'][mods:topic]">
        <crm:P65_shows_visual_item>
            <crm:E36_Visual_Item>
                <crm:P129_is_about rdf:resource="{@valueURI}"/>
            </crm:E36_Visual_Item>
        </crm:P65_shows_visual_item>
    </xsl:template>

    <!-- subjects 'about' -->
    <xsl:template match="mods:subject[@authority = 'lcsh' and child::*[@valueURI]]">
        <crm:P129_is_about>
            <crm:E55_Type>
                <rdfs:label>
                    <xsl:for-each select="*">
                        <xsl:choose>
                            <xsl:when test="self::mods:name">
                                <xsl:value-of select="string-join(mods:namePart, ' ')"/>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:value-of select="normalize-space(.)"/>
                            </xsl:otherwise>
                        </xsl:choose>
                        <xsl:if test="not(position() = last())">
                            <xsl:text>--</xsl:text>
                        </xsl:if>
                    </xsl:for-each>
                </rdfs:label>
                <xsl:if test="*[@valueURI]">
                    <crm:P94i_was_created_by>
                        <crm:E65_Creation>
                            <xsl:apply-templates select="*[@valueURI]" mode="subject"/>
                        </crm:E65_Creation>
                    </crm:P94i_was_created_by>
                </xsl:if>
            </crm:E55_Type>
        </crm:P129_is_about>
    </xsl:template>

    <xsl:template match="mods:subject[@authority = 'lcnaf' and child::mods:name[@valueURI]]">
        <xsl:for-each select="mods:name[@valueURI]">
            <crm:P129_is_about rdf:resource="{@valueURI}"/>
        </xsl:for-each>
    </xsl:template>

    <xsl:template match="*" mode="subject">
        <crm:P15_was_influenced_by rdf:resource="{@valueURI}"/>
    </xsl:template>

    <!-- geographic subjects -->
    <xsl:template match="mods:geographic | *[parent::mods:hierarchicalGeographic]">
        <crm:P129_is_about rdf:resource="{@valueURI}"/>
    </xsl:template>

    <!-- la:Set (collection) -->
    <xsl:template match="mods:relatedItem[@type = 'host' and lower-case(@displayLabel) = 'part of'][mods:location/mods:url]">
        <la:member_of rdf:resource="{mods:location/mods:url}"/>
    </xsl:template>

    <xsl:template match="mods:physicalDescription"> </xsl:template>

    <xsl:template match="mods:extent" mode="statement">
        <crm:P67i_is_referred_to_by>
            <crm:E33_Linguistic_Object>
                <crm:P190_has_symbolic_content>
                    <xsl:value-of select="."/>
                </crm:P190_has_symbolic_content>
                <crm:P2_has_type rdf:resource="http://vocab.getty.edu/aat/300435430"/>
            </crm:E33_Linguistic_Object>
        </crm:P67i_is_referred_to_by>
    </xsl:template>

    <!-- FUNCTIONS -->
    <xsl:function name="mods2la:generateTitle">
        <xsl:param name="titleInfo"/>

        <xsl:value-of select="$titleInfo/mods:title"/>
        <xsl:if test="$titleInfo/mods:subTitle">
            <xsl:text>: </xsl:text>
            <xsl:value-of select="$titleInfo/mods:subTitle"/>
        </xsl:if>
    </xsl:function>

</xsl:stylesheet>
