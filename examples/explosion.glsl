// Enhanced Explosion with sparks and smoke - one-shot effect
// High quality with multiple layers, FBM noise, and particle systems

// Hash functions for randomness
float hash(float n) { return fract(sin(n) * 43758.5453123); }
float hash2(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123); }

// 2D noise
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

// Fractal Brownian Motion for rich detail
float fbm(vec2 p, int octaves) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;
    for(int i = 0; i < 8; i++) {
        if(i >= octaves) break;
        value += amplitude * noise(p * frequency);
        frequency *= 2.0;
        amplitude *= 0.5;
    }
    return value;
}

// Smooth animation curves
float easeOut(float t) { return 1.0 - pow(1.0 - t, 3.0); }
float easeOutQuint(float t) { return 1.0 - pow(1.0 - t, 5.0); }

// Main fireball/explosion core with multiple layers
vec4 explosionCore(vec2 uv, float t) {
    vec2 center = vec2(0.5);
    vec2 dir = uv - center;
    float dist = length(dir);
    float angle = atan(dir.y, dir.x);
    
    // Explosion expands rapidly then contracts
    float expandTime = smoothstep(0.0, 0.1, t);
    float contractTime = smoothstep(0.15, 0.7, t);
    float radius = 0.28 * expandTime * (1.0 - contractTime * 0.95);
    
    // Multiple layers of turbulence for more organic fire look
    float turbulence1 = fbm(vec2(angle * 4.0 + t * 3.0, t * 8.0), 6) * 0.2;
    float turbulence2 = fbm(vec2(angle * 8.0 - t * 5.0, dist * 10.0 + t * 4.0), 5) * 0.1;
    float edgeRadius = radius + (turbulence1 + turbulence2) * radius;
    
    // Multi-layer fire effect
    float core1 = 1.0 - smoothstep(0.0, edgeRadius, dist);
    float core2 = 1.0 - smoothstep(0.0, edgeRadius * 0.7, dist);
    float core3 = 1.0 - smoothstep(0.0, edgeRadius * 0.4, dist);
    
    core1 = pow(core1, 1.2);
    core2 = pow(core2, 1.5);
    core3 = pow(core3, 2.0);
    
    // Dynamic fire pattern
    float firePattern = fbm(uv * 15.0 + vec2(t * 3.0, t * 2.0), 5);
    float fire = core1 * (0.7 + 0.3 * firePattern);
    
    // Color gradient: white hot center -> yellow -> orange -> red -> dark red
    vec3 white = vec3(1.0, 1.0, 0.95);
    vec3 yellow = vec3(1.0, 0.85, 0.2);
    vec3 orange = vec3(1.0, 0.45, 0.05);
    vec3 red = vec3(0.9, 0.15, 0.02);
    vec3 darkRed = vec3(0.4, 0.05, 0.01);
    
    float colorMix = dist / max(edgeRadius, 0.001);
    vec3 color = mix(white, yellow, smoothstep(0.0, 0.2, colorMix));
    color = mix(color, orange, smoothstep(0.2, 0.5, colorMix));
    color = mix(color, red, smoothstep(0.5, 0.8, colorMix));
    color = mix(color, darkRed, smoothstep(0.8, 1.0, colorMix));
    
    // Brighten center
    color += white * core3 * 0.5;
    
    // Fade out over time
    float fadeOut = 1.0 - smoothstep(0.1, 0.6, t);
    float alpha = fire * fadeOut;
    
    // Flickering
    float flicker = 0.85 + 0.15 * noise(vec2(t * 30.0, 0.0));
    alpha *= flicker;
    
    return vec4(color, alpha);
}

// Secondary fire burst layer
vec4 fireBurst(vec2 uv, float t) {
    vec2 center = vec2(0.5);
    vec4 burstColor = vec4(0.0);
    
    // Multiple fire tendrils
    for(int i = 0; i < 12; i++) {
        float fi = float(i);
        float angle = fi * 6.28318 / 12.0 + hash(fi) * 0.5;
        float speed = 0.4 + hash(fi * 1.5) * 0.3;
        
        // Tendril extends outward
        float tendrilT = t * 3.0;
        float tendrilDist = speed * easeOutQuint(min(tendrilT, 1.0)) * 0.25;
        tendrilDist *= 1.0 - smoothstep(0.2, 0.5, t); // Contract back
        
        vec2 tendrilEnd = center + vec2(cos(angle), sin(angle)) * tendrilDist;
        
        // Line from center to tendril end
        vec2 toPoint = uv - center;
        vec2 tendrilDir = normalize(tendrilEnd - center);
        float along = dot(toPoint, tendrilDir);
        float perpDist = length(toPoint - tendrilDir * along);
        
        float inRange = smoothstep(tendrilDist + 0.02, tendrilDist - 0.02, along) * smoothstep(-0.01, 0.02, along);
        float tendrilWidth = 0.025 * (1.0 - along / max(tendrilDist, 0.001)) * (1.0 - t * 1.5);
        float tendril = smoothstep(tendrilWidth, tendrilWidth * 0.3, perpDist) * inRange;
        
        vec3 tColor = mix(vec3(1.0, 0.8, 0.2), vec3(1.0, 0.3, 0.05), along / max(tendrilDist, 0.001));
        burstColor += vec4(tColor * tendril, tendril) * (1.0 - smoothstep(0.3, 0.5, t));
    }
    
    return clamp(burstColor, 0.0, 1.0);
}

// Sparks flying outward
vec4 sparks(vec2 uv, float t) {
    vec2 center = vec2(0.5);
    vec4 sparkColor = vec4(0.0);
    
    // Many sparks
    for(int i = 0; i < 80; i++) {
        float fi = float(i);
        float seed = hash(fi * 127.1);
        float seed2 = hash(fi * 311.7);
        float seed3 = hash(fi * 543.3);
        float seed4 = hash(fi * 789.0);
        
        // Random angle with some clustering
        float angle = seed * 6.28318;
        float speed = 0.25 + seed2 * 0.45;
        float delay = seed3 * 0.08;
        
        float sparkT = max(0.0, t - delay);
        float lifetime = 0.35 + seed2 * 0.35;
        float sparkLife = sparkT / lifetime;
        
        if(sparkLife > 1.0 || sparkLife < 0.0) continue;
        
        // Position with gravity and drag
        float travelDist = speed * sparkT * (1.0 - sparkLife * 0.5);
        vec2 sparkPos = center + vec2(cos(angle), sin(angle)) * travelDist;
        sparkPos.y -= 0.2 * sparkT * sparkT; // Gravity
        
        // Add wobble
        sparkPos.x += sin(sparkT * 20.0 + fi) * 0.005;
        
        // Keep sparks in safe bounds
        if(sparkPos.x < 0.08 || sparkPos.x > 0.92 || sparkPos.y < 0.08 || sparkPos.y > 0.92) continue;
        
        // Spark with trail
        float sparkDist = length(uv - sparkPos);
        float sparkSize = 0.007 * (1.0 - sparkLife * 0.6);
        
        // Bright core
        float spark = 1.0 - smoothstep(0.0, sparkSize, sparkDist);
        spark = pow(spark, 1.5);
        
        // Glow around spark
        float glow = 1.0 - smoothstep(0.0, sparkSize * 3.0, sparkDist);
        glow = pow(glow, 3.0) * 0.3;
        
        // Fade out
        float sparkFade = 1.0 - smoothstep(0.4, 1.0, sparkLife);
        spark *= sparkFade;
        glow *= sparkFade;
        
        // Color: bright yellow -> orange -> red as it cools
        vec3 sColor = mix(vec3(1.0, 0.95, 0.5), vec3(1.0, 0.4, 0.1), sparkLife * 0.7);
        vec3 glowColor = mix(vec3(1.0, 0.7, 0.2), vec3(1.0, 0.2, 0.05), sparkLife);
        
        sparkColor.rgb += sColor * spark + glowColor * glow;
        sparkColor.a = max(sparkColor.a, spark + glow * 0.5);
    }
    
    return clamp(sparkColor, 0.0, 1.0);
}

// Smoke dissipating at edges
vec4 smoke(vec2 uv, float t) {
    vec2 center = vec2(0.5);
    vec4 smokeColor = vec4(0.0);
    
    float smokeStart = 0.12;
    float smokeT = max(0.0, t - smokeStart);
    
    if(smokeT <= 0.0) return smokeColor;
    
    // Multiple smoke puffs
    for(int i = 0; i < 25; i++) {
        float fi = float(i);
        float seed = hash(fi * 234.5);
        float seed2 = hash(fi * 567.8);
        float seed3 = hash(fi * 890.1);
        
        float angle = seed * 6.28318;
        float speed = 0.08 + seed2 * 0.12;
        float puffDelay = seed3 * 0.15;
        
        float puffT = max(0.0, smokeT - puffDelay);
        if(puffT <= 0.0) continue;
        
        // Smoke rises and drifts outward
        float travelDist = speed * puffT;
        vec2 smokePos = center + vec2(cos(angle), sin(angle)) * travelDist * 0.6;
        smokePos.y += 0.12 * puffT; // Rises
        
        // Turbulent motion
        smokePos += vec2(
            fbm(vec2(fi, puffT * 2.0), 4) - 0.5,
            fbm(vec2(fi + 100.0, puffT * 2.0), 4) - 0.5
        ) * 0.08 * puffT;
        
        // Keep in bounds
        smokePos = clamp(smokePos, vec2(0.12), vec2(0.88));
        
        float smokeDist = length(uv - smokePos);
        float smokeSize = 0.04 + puffT * 0.12;
        
        // Billowing smoke shape
        float noiseVal = fbm(uv * 12.0 + vec2(fi * 10.0, puffT * 3.0), 5);
        float puff = 1.0 - smoothstep(0.0, smokeSize, smokeDist + noiseVal * 0.025);
        puff = pow(puff, 1.8);
        
        // Fade out
        float puffFade = 1.0 - smoothstep(0.2, 0.65 - smokeStart, smokeT);
        puff *= puffFade * 0.35;
        
        // Smoke color - dark with slight warm tint from fire
        vec3 sColor = mix(vec3(0.25, 0.18, 0.12), vec3(0.4, 0.25, 0.15), seed * puffFade);
        
        smokeColor.rgb += sColor * puff;
        smokeColor.a = max(smokeColor.a, puff * 0.6);
    }
    
    return clamp(smokeColor, 0.0, 1.0);
}

// Glowing embers floating
vec4 embers(vec2 uv, float t) {
    vec2 center = vec2(0.5);
    vec4 emberColor = vec4(0.0);
    
    float emberStart = 0.25;
    float emberT = max(0.0, t - emberStart);
    
    if(emberT <= 0.0) return emberColor;
    
    for(int i = 0; i < 40; i++) {
        float fi = float(i);
        float seed = hash(fi * 456.7);
        float seed2 = hash(fi * 789.0);
        float seed3 = hash(fi * 123.4);
        
        float angle = seed * 6.28318;
        float startDist = 0.03 + seed2 * 0.2;
        
        // Embers drift slowly upward and outward
        vec2 emberPos = center + vec2(cos(angle), sin(angle)) * startDist;
        emberPos += vec2(
            sin(emberT * 2.5 + fi * 0.5) * 0.03,
            emberT * 0.08 + cos(emberT * 2.0 + fi) * 0.015
        );
        
        // Keep in bounds
        if(emberPos.x < 0.1 || emberPos.x > 0.9 || emberPos.y < 0.1 || emberPos.y > 0.9) continue;
        
        float emberDist = length(uv - emberPos);
        float emberSize = 0.005 * (1.0 - emberT * 0.4);
        
        // Glowing ember
        float ember = 1.0 - smoothstep(0.0, emberSize, emberDist);
        ember = pow(ember, 1.3);
        
        // Soft glow
        float emberGlow = 1.0 - smoothstep(0.0, emberSize * 4.0, emberDist);
        emberGlow = pow(emberGlow, 3.0) * 0.2;
        
        // Pulsing brightness
        float pulse = 0.6 + 0.4 * sin(emberT * 12.0 + fi * 3.0);
        ember *= pulse;
        emberGlow *= pulse;
        
        // Fade out completely by end
        float emberFade = 1.0 - smoothstep(0.25, 0.7 - emberStart, emberT);
        ember *= emberFade;
        emberGlow *= emberFade;
        
        // Warm ember colors
        vec3 eColor = mix(vec3(1.0, 0.5, 0.1), vec3(0.9, 0.25, 0.05), seed3);
        
        emberColor.rgb += eColor * (ember + emberGlow);
        emberColor.a = max(emberColor.a, ember + emberGlow * 0.5);
    }
    
    return clamp(emberColor, 0.0, 1.0);
}

// Expanding shockwave
vec4 shockwave(vec2 uv, float t) {
    vec2 center = vec2(0.5);
    float dist = length(uv - center);
    
    float ringTime = t * 5.0;
    if(ringTime > 1.0) return vec4(0.0);
    
    float ringRadius = ringTime * 0.32;
    float ringWidth = 0.025 * (1.0 - ringTime);
    
    float ring = 1.0 - smoothstep(ringWidth * 0.3, ringWidth, abs(dist - ringRadius));
    ring *= 1.0 - ringTime;
    ring = pow(ring, 1.5);
    
    // Distortion/heat ripple
    float ripple = 1.0 - smoothstep(0.0, ringWidth * 2.0, abs(dist - ringRadius));
    ripple *= (1.0 - ringTime) * 0.3;
    
    vec3 ringColor = mix(vec3(1.0, 0.8, 0.4), vec3(1.0, 0.5, 0.2), ringTime);
    
    return vec4(ringColor * (ring + ripple), (ring + ripple) * 0.7);
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    
    // Global fade out to ensure complete transparency at end
    float globalFade = 1.0 - smoothstep(0.75, 1.0, iTime);
    
    if(globalFade <= 0.0) {
        fragColor = vec4(0.0);
        return;
    }
    
    // Gather all layers
    vec4 core = explosionCore(uv, iTime);
    vec4 burst = fireBurst(uv, iTime);
    vec4 sparkLayer = sparks(uv, iTime);
    vec4 smokeLayer = smoke(uv, iTime);
    vec4 emberLayer = embers(uv, iTime);
    vec4 ring = shockwave(uv, iTime);
    
    // Composite layers
    vec4 result = vec4(0.0);
    
    // Smoke at back
    result = smokeLayer;
    
    // Fire core (additive blending for brightness)
    result.rgb += core.rgb * core.a;
    result.a = max(result.a, core.a);
    
    // Fire burst tendrils
    result.rgb += burst.rgb * burst.a;
    result.a = max(result.a, burst.a);
    
    // Shockwave
    result.rgb += ring.rgb * ring.a;
    result.a = max(result.a, ring.a);
    
    // Sparks (bright, additive)
    result.rgb += sparkLayer.rgb * sparkLayer.a * 1.3;
    result.a = max(result.a, sparkLayer.a);
    
    // Embers
    result.rgb += emberLayer.rgb * emberLayer.a;
    result.a = max(result.a, emberLayer.a);
    
    // Apply global fade
    result *= globalFade;
    
    // HDR-like bloom effect - brighten very bright areas
    float brightness = dot(result.rgb, vec3(0.299, 0.587, 0.114));
    result.rgb += result.rgb * smoothstep(0.8, 1.5, brightness) * 0.3;
    
    fragColor = clamp(result, 0.0, 1.0);
}