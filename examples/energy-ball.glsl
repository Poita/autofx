// Glowing Green Energy Ball with Electric Arcs, Pulsing Core, and Orbiting Particles
// Seamlessly looping animation

#define PI 3.14159265359
#define TAU 6.28318530718

// Hash function for randomness
float hash(float n) {
    return fract(sin(n) * 43758.5453123);
}

float hash2(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}

// Smooth noise
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

// FBM noise for complex textures
float fbm(vec2 p, int octaves) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;
    
    for(int i = 0; i < 6; i++) {
        if(i >= octaves) break;
        value += amplitude * noise(p * frequency);
        frequency *= 2.0;
        amplitude *= 0.5;
    }
    return value;
}

// Looping time helper - completes exactly one cycle over duration
float loopTime(float t, float duration) {
    return sin(t * TAU / duration);
}

float loopTimeCos(float t, float duration) {
    return cos(t * TAU / duration);
}

// Electric arc function
float electricArc(vec2 uv, vec2 start, vec2 end, float time, float seed) {
    vec2 dir = end - start;
    float len = length(dir);
    dir /= len;
    
    vec2 perp = vec2(-dir.y, dir.x);
    vec2 toPoint = uv - start;
    
    float along = dot(toPoint, dir);
    float across = dot(toPoint, perp);
    
    if(along < 0.0 || along > len) return 0.0;
    
    // Use looping noise for the arc displacement
    float loopPhase = fract(time);
    float displacement = 0.0;
    
    // Multiple frequencies of displacement that loop
    for(int i = 0; i < 4; i++) {
        float freq = float(i + 1) * 3.0;
        float amp = 0.03 / float(i + 1);
        displacement += amp * sin(along * freq * 20.0 + loopPhase * TAU + seed * 10.0);
        displacement += amp * 0.5 * sin(along * freq * 35.0 - loopPhase * TAU * 2.0 + seed * 20.0);
    }
    
    float dist = abs(across - displacement);
    
    // Fade at ends
    float fade = smoothstep(0.0, 0.1 * len, along) * smoothstep(len, 0.9 * len, along);
    
    // Arc intensity
    float arc = exp(-dist * 80.0) * fade;
    
    return arc;
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    vec2 center = vec2(0.5);
    vec2 centeredUV = uv - center;
    
    float duration = 1.0;
    float t = iTime;
    float loopT = fract(t / duration); // 0 to 1 looping
    
    // Pulse factors that loop seamlessly
    float pulse1 = 0.5 + 0.5 * sin(loopT * TAU);
    float pulse2 = 0.5 + 0.5 * sin(loopT * TAU + PI * 0.5);
    float pulse3 = 0.5 + 0.5 * sin(loopT * TAU * 2.0);
    
    float dist = length(centeredUV);
    float angle = atan(centeredUV.y, centeredUV.x);
    
    vec3 color = vec3(0.0);
    float alpha = 0.0;
    
    // === CORE ===
    // Inner bright core with pulsing
    float coreRadius = 0.08 + 0.02 * pulse1;
    float coreDist = dist / coreRadius;
    
    // Core glow - bright center
    float coreGlow = exp(-coreDist * 3.0);
    vec3 coreColor = mix(vec3(0.8, 1.0, 0.8), vec3(0.2, 1.0, 0.4), coreDist);
    coreColor = mix(coreColor, vec3(1.0), coreGlow * 0.5);
    
    color += coreColor * coreGlow * (1.0 + 0.3 * pulse3);
    alpha = max(alpha, coreGlow);
    
    // === ENERGY BALL SURFACE ===
    float ballRadius = 0.18 + 0.015 * pulse1;
    
    // Animated surface noise that loops
    vec2 noiseCoord = vec2(angle * 2.0, dist * 10.0);
    float surfaceNoise = fbm(noiseCoord + vec2(loopT * 5.0, loopT * 3.0), 5);
    surfaceNoise += 0.5 * fbm(noiseCoord * 2.0 - vec2(loopT * 8.0, loopT * 2.0), 4);
    
    float surfaceDist = dist - ballRadius + surfaceNoise * 0.03;
    float surface = 1.0 - smoothstep(-0.02, 0.02, surfaceDist);
    float surfaceEdge = exp(-abs(surfaceDist) * 40.0);
    
    vec3 ballColor = mix(vec3(0.1, 0.6, 0.2), vec3(0.3, 1.0, 0.4), surface);
    ballColor += vec3(0.5, 1.0, 0.6) * surfaceEdge * 2.0;
    
    color += ballColor * surface * 0.8;
    alpha = max(alpha, surface * 0.9 + surfaceEdge * 0.5);
    
    // === OUTER GLOW ===
    float outerGlow = exp(-dist * 4.0) * 0.6;
    outerGlow += exp(-(dist - ballRadius) * 8.0) * 0.4 * step(0.0, dist - ballRadius * 0.5);
    color += vec3(0.2, 0.8, 0.3) * outerGlow * (1.0 + 0.2 * pulse2);
    alpha = max(alpha, outerGlow * 0.7);
    
    // === ELECTRIC ARCS ===
    float arcIntensity = 0.0;
    
    // Multiple arcs emanating from center
    for(int i = 0; i < 8; i++) {
        float arcAngle = float(i) * TAU / 8.0 + loopT * TAU * 0.5;
        float arcLen = 0.15 + 0.08 * sin(loopT * TAU * 3.0 + float(i) * 1.5);
        
        vec2 arcStart = center + vec2(cos(arcAngle), sin(arcAngle)) * ballRadius * 0.8;
        vec2 arcEnd = center + vec2(cos(arcAngle), sin(arcAngle)) * (ballRadius + arcLen);
        
        // Keep arcs within bounds
        arcEnd = clamp(arcEnd, vec2(0.08), vec2(0.92));
        
        float arc = electricArc(uv, arcStart, arcEnd, loopT, float(i));
        arcIntensity += arc * (0.5 + 0.5 * sin(loopT * TAU * 4.0 + float(i) * 2.0));
    }
    
    // Secondary smaller arcs
    for(int i = 0; i < 12; i++) {
        float arcAngle = float(i) * TAU / 12.0 + loopT * TAU * 0.3 + PI / 12.0;
        float arcLen = 0.08 + 0.04 * sin(loopT * TAU * 2.0 + float(i) * 2.5);
        
        vec2 arcStart = center + vec2(cos(arcAngle), sin(arcAngle)) * ballRadius * 0.9;
        vec2 arcEnd = center + vec2(cos(arcAngle), sin(arcAngle)) * (ballRadius + arcLen);
        
        arcEnd = clamp(arcEnd, vec2(0.08), vec2(0.92));
        
        float arc = electricArc(uv, arcStart, arcEnd, loopT + 0.5, float(i) + 100.0);
        arcIntensity += arc * 0.6 * (0.5 + 0.5 * sin(loopT * TAU * 5.0 + float(i) * 3.0));
    }
    
    vec3 arcColor = mix(vec3(0.4, 1.0, 0.6), vec3(0.8, 1.0, 0.9), arcIntensity);
    color += arcColor * arcIntensity * 2.0;
    alpha = max(alpha, arcIntensity);
    
    // === ORBITING PARTICLES ===
    float particleGlow = 0.0;
    
    // Multiple orbit layers
    for(int layer = 0; layer < 3; layer++) {
        float orbitRadius = 0.22 + float(layer) * 0.06;
        float orbitSpeed = 1.0 + float(layer) * 0.3;
        float orbitTilt = float(layer) * 0.4;
        
        for(int i = 0; i < 8; i++) {
            float particleAngle = float(i) * TAU / 8.0 + loopT * TAU * orbitSpeed;
            particleAngle += float(layer) * PI / 8.0; // Offset layers
            
            // 3D orbit projected to 2D
            float z = sin(particleAngle) * sin(orbitTilt);
            float projectedRadius = orbitRadius * (1.0 + z * 0.2);
            float brightness = 0.6 + 0.4 * (z + 1.0) * 0.5; // Depth-based brightness
            
            vec2 particlePos = center + vec2(
                cos(particleAngle) * projectedRadius,
                sin(particleAngle) * cos(orbitTilt) * projectedRadius
            );
            
            float particleDist = length(uv - particlePos);
            float particleSize = 0.012 + 0.004 * sin(loopT * TAU * 3.0 + float(i));
            
            float particle = exp(-particleDist / particleSize * 2.0) * brightness;
            particleGlow += particle;
            
            // Particle trail
            for(int t = 1; t < 6; t++) {
                float trailAngle = particleAngle - float(t) * 0.08 * orbitSpeed;
                float tz = sin(trailAngle) * sin(orbitTilt);
                float tRadius = orbitRadius * (1.0 + tz * 0.2);
                
                vec2 trailPos = center + vec2(
                    cos(trailAngle) * tRadius,
                    sin(trailAngle) * cos(orbitTilt) * tRadius
                );
                
                float trailDist = length(uv - trailPos);
                float trailSize = particleSize * (1.0 - float(t) * 0.15);
                float trail = exp(-trailDist / trailSize * 2.5) * brightness * (1.0 - float(t) * 0.18);
                particleGlow += trail * 0.5;
            }
        }
    }
    
    vec3 particleColor = mix(vec3(0.3, 1.0, 0.5), vec3(0.7, 1.0, 0.8), particleGlow);
    color += particleColor * particleGlow * 1.5;
    alpha = max(alpha, particleGlow * 0.8);
    
    // === ENERGY WISPS ===
    for(int i = 0; i < 6; i++) {
        float wispAngle = float(i) * TAU / 6.0 + loopT * TAU * 0.7;
        float wispRadius = 0.12 + 0.04 * sin(loopT * TAU * 2.0 + float(i) * 1.5);
        
        vec2 wispPos = center + vec2(cos(wispAngle), sin(wispAngle)) * wispRadius;
        float wispDist = length(uv - wispPos);
        
        float wisp = exp(-wispDist * 30.0) * (0.5 + 0.5 * pulse2);
        color += vec3(0.4, 1.0, 0.6) * wisp;
        alpha = max(alpha, wisp * 0.6);
    }
    
    // === FINAL ADJUSTMENTS ===
    // Add subtle chromatic variation
    color.r *= 0.9 + 0.1 * sin(dist * 20.0 + loopT * TAU);
    color.b *= 0.85 + 0.15 * sin(angle * 3.0 + loopT * TAU);
    
    // Boost overall brightness
    color *= 1.2;
    
    // Ensure we stay within bounds - fade at edges
    float edgeFade = smoothstep(0.0, 0.08, uv.x) * smoothstep(1.0, 0.92, uv.x);
    edgeFade *= smoothstep(0.0, 0.08, uv.y) * smoothstep(1.0, 0.92, uv.y);
    alpha *= edgeFade;
    color *= edgeFade;
    
    // Clamp alpha
    alpha = clamp(alpha, 0.0, 1.0);
    
    fragColor = vec4(color, alpha);
}