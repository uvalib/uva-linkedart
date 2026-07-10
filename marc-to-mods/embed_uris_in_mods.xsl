<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns="http://www.loc.gov/mods/v3" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:math="http://www.w3.org/2005/xpath-functions/math" xmlns:xpf="http://www.w3.org/2005/xpath-functions" xmlns:mods="http://www.loc.gov/mods/v3"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#" xmlns:skos="http://www.w3.org/2004/02/skos/core#"
    exclude-result-prefixes="#all" version="3.0">

    <xsl:output method="xml" encoding="UTF-8" indent="true"/>

    <xsl:variable name="resolver-url">http://127.0.0.1:8001/</xsl:variable>

    <xsl:variable name="resolver-on" as="xs:boolean">
        <xsl:value-of select="unparsed-text-available($resolver-url)"/>
    </xsl:variable>

    <xsl:variable name="marcCountries" as="node()">
        <xsl:copy-of select="document('countries.skosrdf.xml')"/>
    </xsl:variable>

    <xsl:template match="@* | node()">
        <xsl:copy>
            <xsl:apply-templates select="@* | node()"/>
        </xsl:copy>
    </xsl:template>

    <!-- names -->
    <xsl:template match="mods:name[@type]">
        <xsl:choose>
            <xsl:when test="$resolver-on = true()">

                <xsl:variable name="api-response" as="node()">
                    <xsl:copy-of select="json-to-xml(unparsed-text(concat($resolver-url, 'query/cpf?term=', encode-for-uri(string-join(mods:namePart, ' ')))))"/>
                </xsl:variable>

                <xsl:element name="{name()}">
                    <xsl:attribute name="type" select="@type"/>

                    <xsl:if test="$api-response//xpf:string[@key = 'uri']">
                        <xsl:attribute name="valueURI" select="$api-response//xpf:string[@key = 'uri']"/>
                    </xsl:if>

                    <xsl:apply-templates select="*"/>

                </xsl:element>
            </xsl:when>
            <xsl:otherwise>
                <xsl:copy>
                    <xsl:apply-templates select="@* | node()"/>
                </xsl:copy>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <!-- subjects -->
    <xsl:template match="mods:subject[@authority = 'lcsh']">
        <xsl:choose>
            <xsl:when test="$resolver-on = true()">
                <subject authority="lcsh">
                    <xsl:apply-templates select="*" mode="lcsh"/>
                </subject>
            </xsl:when>
            <xsl:otherwise>
                <xsl:copy>
                    <xsl:apply-templates select="@* | node()"/>
                </xsl:copy>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xsl:template match="*" mode="lcsh">
        <xsl:variable name="term" select="if (name() = 'name') then string-join(mods:namePart, ' ') else ."/>
        
        <xsl:variable name="api-response" as="node()">
            <xsl:copy-of select="json-to-xml(unparsed-text(concat($resolver-url, 'query/subjects?term=', encode-for-uri($term))))"/>
        </xsl:variable>
        
        <xsl:choose>
            <xsl:when test="name() = 'name' or name() = 'titleInfo'">
                <xsl:element name="{name()}">
                    <xsl:apply-templates select="@*[not(name() = 'valueURI')]"/>
                    
                    <xsl:if test="$api-response//xpf:string[@key = 'uri']">
                        <xsl:attribute name="valueURI" select="$api-response//xpf:string[@key = 'uri']"/>
                    </xsl:if>
                    
                    <xsl:apply-templates select="*"/>
                </xsl:element>
            </xsl:when>
            <xsl:otherwise>                
                <xsl:element name="{name()}">
                    <!-- don't insert valueURI into mods:namePart -->
                    <xsl:if test="$api-response//xpf:string[@key = 'uri'] and not(parent::mods:name)">
                        <xsl:attribute name="valueURI" select="$api-response//xpf:string[@key = 'uri']"/>
                    </xsl:if>
                    
                    <xsl:value-of select="."/>
                </xsl:element>
            </xsl:otherwise>
        </xsl:choose>
        
    </xsl:template>

    <!-- strip duplicate titles -->
    <xsl:template match="mods:titleInfo[@type]">
        <xsl:if test="not(text() = preceding::mods:titleInfo/text())">
            <xsl:copy>
                <xsl:apply-templates select="@* | node()"/>
            </xsl:copy>
        </xsl:if>
    </xsl:template>

    <xsl:template match="mods:originInfo/mods:place/mods:placeTerm[@type = 'text']">
        <xsl:choose>
            <xsl:when test="$resolver-on = true()">
                <xsl:choose>
                    <xsl:when test="ancestor::mods:originInfo/mods:place/mods:placeTerm[@type = 'code' and @authority = 'marccountry']">
                        <xsl:variable name="marcCountry" select="ancestor::mods:originInfo/mods:place/mods:placeTerm[@type = 'code' and @authority = 'marccountry']"/>
                        
                        <xsl:choose>
                            <xsl:when test="not($marcCountry = 'xx')">
                                <xsl:variable name="term"> 
                                    <xsl:value-of select="."/>
                                    <xsl:text>, </xsl:text>
                                    <xsl:value-of select="$marcCountries//*[skos:notation = $marcCountry]/skos:prefLabel[@xml:lang = 'en']"/>                        
                                </xsl:variable>
                                
                                <xsl:variable name="api-response" as="node()">
                                    <xsl:copy-of select="json-to-xml(unparsed-text(concat($resolver-url, 'query/places?term=', encode-for-uri($term))))"/>
                                </xsl:variable>
                                
                                <xsl:element name="{name()}">
                                    <xsl:attribute name="type">text</xsl:attribute>
                                    <xsl:if test="$api-response//xpf:string[@key = 'uri']">
                                        <xsl:attribute name="valueURI" select="$api-response//xpf:string[@key = 'uri']"/>
                                    </xsl:if>
                                    
                                    <xsl:value-of select="."/>
                                </xsl:element>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:copy-of select="self::node()"/>
                            </xsl:otherwise>
                        </xsl:choose>
                        
                        
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:copy-of select="self::node()"/>
                    </xsl:otherwise>
                </xsl:choose>
            </xsl:when>
            <xsl:otherwise>
                <xsl:copy-of select="self::node()"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    
    <xsl:template match="mods:subject/mods:hierarchicalGeographic">
        <xsl:choose>
            <xsl:when test="$resolver-on = true()">
                <xsl:element name="hierarchicalGeographic" namespace="http://www.loc.gov/mods/v3">
                    
                    <xsl:variable name="term">
                        <xsl:choose>
                            <xsl:when test="count(*) &gt; 1">
                                <xsl:variable name="last" as="node()">
                                    <xsl:copy-of select="*[last()]"/>
                                </xsl:variable>
                                
                                <xsl:variable name="pen" as="node()">
                                    <xsl:copy-of select="*[last() - 1]"/>
                                </xsl:variable>  
                                
                                <xsl:choose>
                                    <xsl:when test="$last/name() = 'city'">
                                        <xsl:choose>
                                            <xsl:when test="$pen/name() = 'state' or $pen/name() = 'province' or $pen/name() = 'country'">
                                                <xsl:value-of select="$last"/>
                                                <xsl:text>, </xsl:text>
                                                <xsl:value-of select="$pen"/>
                                            </xsl:when>
                                            <xsl:otherwise>
                                                <xsl:value-of select="$last"/>
                                            </xsl:otherwise>
                                        </xsl:choose>
                                        
                                    </xsl:when>
                                    <xsl:otherwise>
                                        <xsl:value-of select="."/>
                                    </xsl:otherwise>
                                </xsl:choose>
                                
                                
                            </xsl:when>
                            <xsl:when test="count(*) = 1">
                                <xsl:value-of select="child::*/text()"/>
                            </xsl:when>
                        </xsl:choose>
                    </xsl:variable>
                    
                    <xsl:copy-of select="*[not(position() = last())]"/>
                    
                    <xsl:apply-templates select="*[position() = last()]" mode="geo-hier">
                        <xsl:with-param name="term" select="$term"/>
                    </xsl:apply-templates>
                </xsl:element>
            </xsl:when>
            <xsl:otherwise>
                <xsl:copy-of select="self::node()"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    
    <xsl:template match="mods:subject/mods:geographic">
        <xsl:choose>
            <xsl:when test="$resolver-on = true()">
                <xsl:apply-templates select="self::node()" mode="geo-hier">
                    <xsl:with-param name="term" select="."/>
                </xsl:apply-templates>
            </xsl:when>
            <xsl:otherwise>
                <xsl:copy-of select="self::node()"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    
    <xsl:template match="*" mode="geo-hier">
        <xsl:param name="term"/>
        
        <xsl:variable name="api-response" as="node()">
            <xsl:copy-of select="json-to-xml(unparsed-text(concat($resolver-url, 'query/places?term=', encode-for-uri($term))))"/>
        </xsl:variable>
        
        <xsl:element name="{name()}">                
            <xsl:if test="$api-response//xpf:string[@key = 'uri']">
                <xsl:attribute name="valueURI" select="$api-response//xpf:string[@key = 'uri']"/>
            </xsl:if>
            
            <xsl:value-of select="."/>
        </xsl:element>
    </xsl:template>
    
    <xsl:template match="mods:role">
        <xsl:choose>
            <xsl:when test="$resolver-on = true()">
                <xsl:variable name="term" select="mods:roleTerm"/>
                
                <xsl:variable name="api-response" as="node()">
                    <xsl:copy-of select="json-to-xml(unparsed-text(concat($resolver-url, 'query/relators?term=', encode-for-uri($term))))"/>
                </xsl:variable>
                
                <xsl:if test="$api-response//xpf:string[@key = 'uri']">
                    <xsl:element name="role">
                        <xsl:element name="roleTerm">
                            <xsl:attribute name="type">text</xsl:attribute>
                            <xsl:attribute name="authority">marcrelator</xsl:attribute>
                            <xsl:attribute name="valueURI" select="$api-response//xpf:string[@key = 'uri']"/>
                            <xsl:value-of select="$api-response//xpf:string[@key = 'label']"/>
                        </xsl:element>
                    </xsl:element>
                </xsl:if>
            </xsl:when>
            <xsl:otherwise>
                <xsl:copy-of select="self::node()"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    
    <xsl:template match="mods:dateCreated | mods:dateIssued">
        <xsl:element name="{name()}">
            <xsl:choose>
                <xsl:when test=". castable as xs:date or . castable as xs:dateTime or . castable as xs:gYear or . castable as xs:gYearMonth">
                    <xsl:attribute name="encoding">iso8601</xsl:attribute>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:if test="@encoding">
                        <xsl:attribute name="encoding" select="@encoding"/>
                    </xsl:if>
                </xsl:otherwise>
            </xsl:choose>
            <xsl:apply-templates select="@*[not(name() = 'encoding')]"/>
            
            <xsl:choose>
                <xsl:when test="matches(., '^\d+u+$')">
                    <xsl:value-of select="translate(., 'u', 'X')"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="."/>
                </xsl:otherwise>
            </xsl:choose>            
        </xsl:element>
    </xsl:template>
    
    <xsl:template match="mods:typeOfResource">
        <xsl:element name="typeOfResource">
            <xsl:choose>
                <xsl:when test=". = 'text'">
                    <xsl:attribute name="valueURI">http://vocab.getty.edu/aat/300263751</xsl:attribute>
                    <xsl:text>texts (documents)</xsl:text>
                </xsl:when>
                <xsl:when test=". = 'cartographic'">
                    <xsl:attribute name="valueURI">http://vocab.getty.edu/aat/300028052</xsl:attribute>
                    <xsl:text>cartographic materials</xsl:text>
                </xsl:when>
                <xsl:when test=". = 'notated music'">
                    <xsl:attribute name="valueURI">http://vocab.getty.edu/aat/300417622</xsl:attribute>
                    <xsl:text>musical notation</xsl:text>
                </xsl:when>
                <xsl:when test=". = 'sound recording-nonmusical'">
                    <xsl:attribute name="valueURI">http://vocab.getty.edu/aat/300028633</xsl:attribute>
                    <xsl:text>sound recordings</xsl:text>
                </xsl:when>
                <xsl:when test=". = 'sound recording-musical'">
                    <xsl:attribute name="valueURI">http://vocab.getty.edu/aat/300028633</xsl:attribute>
                    <xsl:text>sound recordings</xsl:text>
                </xsl:when>
                <xsl:when test=". = 'still image'">
                    <xsl:attribute name="valueURI">http://vocab.getty.edu/aat/300264387</xsl:attribute>
                    <xsl:text>images (object genre)</xsl:text>
                </xsl:when>
                <xsl:when test=". = 'moving image'">
                    <xsl:attribute name="valueURI">http://vocab.getty.edu/aat/300263857</xsl:attribute>
                    <xsl:text>moving images</xsl:text>
                </xsl:when>
                <xsl:when test=". = 'three dimensional object'">
                    <xsl:attribute name="valueURI">http://vocab.getty.edu/aat/300117127</xsl:attribute>
                    <xsl:text>artifacts (object genre)</xsl:text>
                </xsl:when>
                <xsl:when test=". = 'software, multimedia'">
                    <xsl:attribute name="valueURI">http://vocab.getty.edu/aat/300028566</xsl:attribute>
                    <xsl:text>software</xsl:text>
                </xsl:when>
                <xsl:when test=". = 'mixed material'">
                    <xsl:attribute name="valueURI">http://vocab.getty.edu/aat/300404821</xsl:attribute>
                    <xsl:text>multiple materials (materials for groups)</xsl:text>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="."/>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:element>
    </xsl:template>
    
    <xsl:template match="mods:genre[@authority]">
        <xsl:choose>
            <xsl:when test="$resolver-on = true()">
                <xsl:variable name="term" select="."/>
                
                <xsl:variable name="api-response" as="node()">
                    <xsl:copy-of select="json-to-xml(unparsed-text(concat($resolver-url, 'query/genres?term=', encode-for-uri($term))))"/>
                </xsl:variable>
                
                <xsl:choose>
                    <xsl:when test="$api-response//xpf:string[@key = 'uri']">
                        <xsl:element name="{name()}">
                            <xsl:attribute name="valueURI" select="$api-response//xpf:string[@key = 'uri']"/>
                            <xsl:attribute name="authority" select="@authority"/>
                            <xsl:value-of select="$api-response//xpf:string[@key = 'label']"/>
                        </xsl:element>                        
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:copy-of select="self::node()"/>
                    </xsl:otherwise>
                </xsl:choose>
            </xsl:when>
            <xsl:otherwise>
                <xsl:copy-of select="self::node()"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    
    <!-- use the SIRSI ckey to look up the Tracksys API to extract the PID (eliminate need for PID as a param -->
    <xsl:template match="mods:recordIdentifier[@source = 'SIRSI']">
        <xsl:copy-of select="self::node()"/>
        
        <xsl:variable name="ckey" select="normalize-space(.)"/>
        
        <xsl:variable name="api-response" as="node()">
            <node>
                <xsl:if test="unparsed-text-available(concat('https://tracksys-api-ws-dev.internal.lib.virginia.edu/api/catkey/', encode-for-uri($ckey)))">
                    <xsl:copy-of select="json-to-xml(unparsed-text(concat('https://tracksys-api-ws-dev.internal.lib.virginia.edu/api/catkey/', encode-for-uri($ckey))))"/>
                </xsl:if>
            </node>
        </xsl:variable>
        
        <xsl:if test="$api-response//xpf:string[@key = 'pid']">
            <xsl:element name="recordIdentifier" namespace="http://www.loc.gov/mods/v3">
                <xsl:attribute name="source">PID</xsl:attribute>
                <xsl:value-of select="$api-response//xpf:string[@key = 'pid']"/>
            </xsl:element>                        
        </xsl:if>
    </xsl:template>

</xsl:stylesheet>
