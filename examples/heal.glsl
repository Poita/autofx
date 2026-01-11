// Healing Aura with Golden Particles - Final
// Seamlessly looping over 1.5 seconds

#define PI 3.14159265359
#define TAU 6.28318530718
#define DURATION 1.5

float hash(float n) {
    return fract(sin(n) * 43758.5453123);
}

float hash2(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}

vec2 hash22(vec2 p) {
    return fract(sin(vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)))) * 43758.5453);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    
    float a = hash2(i);
    float b = hash2(i + vec2(1.0, 0.0));
    float c = hash2(i + vec2(0.0, 1.0));
    float d = hash2(i + vec2(1.0, 1.0));
    
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;
    for (int i = 0; i < 5; i++) {
        value += amplitude * noise(p * frequency);
        amplitude *= 0.5;
        frequency *= 2.0;
    }
    return value;
}

float cycleTime() {
    return iTime * TAU / DURATION;
}

float glow(float d, float radius, float intensity) {
    return intensity / (1.0 + pow(d / radius, 2.0));
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    vec2 centered = uv - 0.5;
    
    // Keep effect within bounds
    float margin = 0.1;
    vec2 scaledUV = centered / (0.5 - margin);
    
    float dist = length(scaledUV);
    float angle = atan(scaledUV.y, scaledUV.x);
    
    float t = cycleTime();
    float tNorm = fract(iTime / DURATION);
    
    vec3 color = vec3(0.0);
    float alpha = 0.0;
    
    // Warm golden palette
    vec3 goldBright = vec3(1.0, 0.8, 0.2);
    vec3 goldWarm = vec3(1.0, 0.65, 0.15);
    vec3 goldSoft = vec3(1.0, 0.88, 0.4);
    vec3 warmWhite = vec3(1.0, 0.95, 0.85);
    
    // === BREATHING AURA CORE ===
    float breathe = 0.5 + 0.25 * sin(t);
    float coreGlow = glow(dist, 0.35 * breathe, 0.7);
    
    vec3 auraColor = mix(goldBright, goldWarm, smoothstep(0.0, 0.6, dist));
    color += auraColor * coreGlow;
    alpha += coreGlow * 0.95;
    
    // Bright inner center
    float innerCore = glow(dist, 0.1 * breathe, 0.5);
    color += warmWhite * innerCore;
    alpha += innerCore * 0.6;
    
    // === ORGANIC FLOWING ENERGY ===
    float flowSpeed = t * 0.4;
    vec2 flowUV = scaledUV * 2.5;
    float flow1 = fbm(flowUV + vec2(sin(flowSpeed), cos(flowSpeed)));
    float flow2 = fbm(flowUV * 1.3 - vec2(cos(flowSpeed * 0.8), sin(flowSpeed * 0.8)));
    
    float auraWave = (flow1 + flow2) * 0.5;
    float auraMask = smoothstep(0.85, 0.0, dist) * smoothstep(0.0, 0.12, dist);
    float auraIntensity = auraWave * auraMask * (0.5 + 0.2 * sin(t));
    
    vec3 waveColor = mix(goldSoft, goldWarm, auraWave);
    color += waveColor * auraIntensity;
    alpha += auraIntensity * 0.7;
    
    // === RISING GOLDEN PARTICLES ===
    for (int i = 0; i < 45; i++) {
        float fi = float(i);
        
        // Spawn position
        vec2 basePos = hash22(vec2(fi, fi * 0.7)) * 1.2 - 0.6;
        basePos.x *= 0.75;
        
        // Cyclic rise with staggered offsets
        float riseSpeed = 0.6 + hash(fi * 3.7) * 0.4;
        float riseOffset = hash(fi * 5.3);
        float rise = fract(tNorm * riseSpeed + riseOffset);
        
        float yPos = mix(-0.65, 0.65, rise);
        
        // Gentle sway
        float swayAmount = 0.08 + hash(fi * 2.1) * 0.07;
        float swaySpeed = 1.0 + hash(fi * 4.2) * 0.6;
        float xOffset = sin(t * swaySpeed + fi * 0.8) * swayAmount;
        
        vec2 particlePos = vec2(basePos.x + xOffset, yPos);
        float pDist = length(scaledUV - particlePos);
        
        // Varied particle sizes
        float pSize = 0.025 + hash(fi * 1.3) * 0.03;
        
        // Smooth fade for looping
        float fadeMask = smoothstep(0.0, 0.18, rise) * smoothstep(1.0, 0.82, rise);
        
        // Stronger near center
        float centerInfluence = smoothstep(0.75, 0.25, length(particlePos));
        
        float pGlow = glow(pDist, pSize, 0.04) * fadeMask * centerInfluence;
        
        vec3 pCol = mix(goldBright, goldSoft, hash(fi));
        
        color += pCol * pGlow;
        alpha += pGlow * 0.9;
    }
    
    // === TWINKLING SPARKLES ===
    for (int i = 0; i < 30; i++) {
        float fi = float(i);
        
        vec2 sparklePos = hash22(vec2(fi * 1.2, fi * 2.5)) * 1.1 - 0.55;
        sparklePos *= 0.72;
        
        // Cyclic twinkle
        float twinklePhase = hash(fi * 7.1) * TAU;
        float twinkleSpeed = 2.5 + hash(fi * 3.3) * 3.5;
        float twinkle = pow(max(0.0, sin(t * twinkleSpeed + twinklePhase)), 4.0);
        
        float sDist = length(scaledUV - sparklePos);
        
        // 4-point star shape
        vec2 sDir = scaledUV - sparklePos;
        float sAngle = atan(sDir.y, sDir.x);
        float starShape = 0.5 + 0.5 * cos(sAngle * 4.0);
        
        float sSize = 0.015 + hash(fi * 4.4) * 0.012;
        float sGlow = glow(sDist, sSize * (1.0 + starShape * 0.7), 0.025) * twinkle;
        
        vec3 sCol = mix(warmWhite, goldSoft, 0.25);
        
        color += sCol * sGlow;
        alpha += sGlow * 0.85;
    }
    
    // === SOFT OUTER RING ===
    float ringRadius = 0.58 + 0.07 * sin(t);
    float ringWidth = 0.18;
    float ring = smoothstep(ringRadius + ringWidth, ringRadius, dist) * 
                 smoothstep(ringRadius - ringWidth * 1.8, ringRadius - ringWidth * 0.4, dist);
    ring *= 0.3 + 0.15 * sin(t * 2.0);
    
    color += goldWarm * ring * 0.6;
    alpha += ring * 0.4;
    
    // === SUBTLE LIGHT RAYS ===
    float rays = 0.0;
    for (int i = 0; i < 6; i++) {
        float fi = float(i);
        float rayAngle = fi * TAU / 6.0 + t * 0.15;
        float angleDiff = abs(mod(angle - rayAngle + PI, TAU) - PI);
        float ray = smoothstep(0.35, 0.0, angleDiff) * smoothstep(0.75, 0.15, dist) * smoothstep(0.0, 0.12, dist);
        rays += ray * 0.06;
    }
    color += goldSoft * rays;
    alpha += rays * 0.35;
    
    // === FINAL OUTPUT ===
    float boundsFade = smoothstep(1.0, 0.6, dist);
    alpha *= boundsFade;
    color *= boundsFade;
    
    alpha = clamp(alpha, 0.0, 1.0);
    
    // Soft tone mapping
    color = color / (1.0 + color * 0.25);
    
    // Enhance warmth
    float luma = dot(color, vec3(0.299, 0.587, 0.114));
    color = mix(vec3(luma), color, 1.2);
    
    fragColor = vec4(color, alpha);
}