# Calculated Question Extraction Summary

Exam: **Final Examination** (ID: 204128)

## Format Analysis

### 1. exportAssessment.txt
**Status:** Does NOT contain Calculated Question data
- This is a plain text format showing only question text
- Contains 3 Essay questions
- No variable, formula, or calculation information

---

### 2. exported-assessment.xml (QTI Format)
**Status:** CONTAINS Calculated Question data
- Full QTI 1.x XML format
- Item ID: 4159415
- Title: "Calculated Question"

#### Question Text:
Uses decimal notation. Consider a competitive industry (firms are price takers). There are {n} firms. The inverse demand function is P={A}-{B}Q and the total cost function of a firm is C(q)={F}+{D}q+{C}q². The supply function of an individual firm is then q(P)={{a}}P²+{{b}}P+{{c}} (coefficients as decimal numbers). The short-run equilibrium price is {{p}} and the firm profits are {{r}}.

Now, assume one of the firms can create an innovation reducing costs by factor {z}. With no patents and no first-mover advantage, the new individual supply function is q(P)={{aa}}P²+{{bb}}P+{{cc}}. The short-run equilibrium price is {{pp}} and profits are {{rr}}.

#### Variables (7 total):
| Variable | Min | Max | Decimal Places |
|----------|-----|-----|----------------|
| A        | 900 | 1000| 0              |
| B        | 1   | 3   | 2              |
| F        | 1   | 4   | 1              |
| D        | 1   | 4   | 1              |
| C        | 1   | 2   | 1              |
| n        | 3   | 10  | 0              |
| z        | 2   | 3   | 2              |

#### Formulas (11 total):
| Name | Formula | Tolerance | Decimal Places |
|------|---------|-----------|----------------|
| a    | {C}-{C} | 0.01      | 3              |
| b    | 1/(2*{C}) | 0.01    | 3              |
| c    | -{D}/(2*{C}) | 0.01 | 3              |
| p    | (2*{A}*{C} + {B}*{D}*{n})/(2*{C} + {B}*{n}) | 0.01 | 3 |
| r    | ({A}^2*{C} - 2*{A}*{C}*{D} - 4*{C}^2*{F} - {B}^2*{F}*{n}^2 + {C}*({D}^2-4*{B}*{F}*{n}))/(2*{C} + {B}*{n})^2 | 0.01 | 3 |
| aa   | {C}-{C} | 0.01      | 3              |
| bb   | {z}/(2*{C}) | 0.01  | 3              |
| cc   | -{D}/(2*{C}) | 0.01 | 3              |
| pp   | (2*{A}*{C} + {B}*{D}*{n})/(2*{C} + {B}*{n}*{z}) | 0.01 | 3 |
| rr   | (-4*{C}^2*{F} -{B}^2*{F}*({n}*{z})^2 + {C}*({D}^2 - 2*{A}*{D}*{z} + {z}*(-4*{B}*{F}*{n} + {A}^2*{z})))/({z}*(2*{C} + {B}*{n}*{z})^2) | 0.01 | 3 |

#### Key XML Structure Elements:
```xml
<item ident="4159415" title="Calculated Question">
  <itemmetadata>
    <qtimetadata>
      <qtimetadatafield>
        <fieldlabel>qmd_itemtype</fieldlabel>
        <fieldentry>Calculated Question</fieldentry>
      </qtimetadatafield>
    </qtimetadata>
  </itemmetadata>

  <presentation>
    <flow class="Block">
      <material>
        <mattext><!-- Question text with {variables} and {{formulas}} --></mattext>
      </material>

      <variables>
        <variable>
          <name>A</name>
          <min>900</min>
          <max>1000</max>
          <decimalPlaces>0</decimalPlaces>
        </variable>
        <!-- ... more variables ... -->
      </variables>

      <formulas>
        <formula>
          <name>a</name>
          <formula>{C}-{C}</formula>
          <tolerance>0.01</tolerance>
          <decimalPlaces>3</decimalPlaces>
        </formula>
        <!-- ... more formulas ... -->
      </formulas>
    </flow>
  </presentation>
</item>
```

---

### 3. exportAssessment.zip → exportAssessment.xml (IMS QTI Package)
**Status:** CONTAINS Calculated Question data (IDENTICAL to exported-assessment.xml)
- This is the same QTI XML content packaged with an IMS manifest
- The zip also contains `imsmanifest.xml` which references the assessment XML
- All Calculated Question data is identical to Format #2

---

## Summary

**Calculated Question Support by Format:**
1. ✗ Plain Text (.txt) - No support
2. ✓ QTI XML (.xml) - Full support with all variables and formulas
3. ✓ IMS QTI Package (.zip) - Full support (contains same XML as #2)

**Variable Notation:**
- Variables in question text: `{variableName}` (single braces)
- Formulas/calculations in question text: `{{formulaName}}` (double braces)
- Alternative notation seen: `[[{variableName}]]` (bracketed variables)

**Key Features:**
- 7 random variables with configurable ranges and decimal precision
- 11 calculated formulas with tolerance specifications
- Variables can be reused in multiple formulas
- Supports complex mathematical expressions (powers, fractions, nested operations)
- Score: 20 points maximum
